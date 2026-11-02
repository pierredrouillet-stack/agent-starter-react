"""Facts the agent remembers about a user across calls.

See docs/conversation-storage.md for the table this module reads and writes.
"""

import asyncio
import json
import logging
import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass

from livekit.agents import llm

from recorder import db_path_from_env, iso_utc, open_db

logger = logging.getLogger("memory")


def parse_user(metadata: str | None) -> str | None:
    """Read a user id from job metadata; None if absent or unusable."""
    if not metadata or not metadata.strip():
        return None
    try:
        data = json.loads(metadata)
    except ValueError:
        return None  # not ours to report: parse_resume logs unusable metadata
    if not isinstance(data, dict) or "user" not in data:
        return None
    user_id = data["user"]
    if not isinstance(user_id, str) or not user_id:
        logger.warning("ignoring user: expected a non-empty string")
        return None
    return user_id


# The most facts kept for one user; the oldest are dropped beyond it.
MAX_FACTS = 50


@dataclass(frozen=True)
class Fact:
    id: int
    text: str
    learned_at: str
    source_conversation_id: str | None


def load_facts(conn: sqlite3.Connection, user_id: str) -> list[Fact]:
    """A user's facts, oldest first."""
    rows = conn.execute(
        "SELECT id, fact, learned_at, source_conversation_id FROM user_facts "
        "WHERE user_id = ? ORDER BY learned_at, id",
        (user_id,),
    ).fetchall()
    return [Fact(*row) for row in rows]


def load_user_facts(user_id: str | None) -> list[Fact]:
    """The facts to give a session at its start; any failure means none."""
    path = db_path_from_env()
    if not user_id or path is None:
        return []
    try:
        conn = open_db(path)
        try:
            return load_facts(conn, user_id)
        finally:
            conn.close()
    except Exception as exc:
        logger.warning("could not read the user's facts: %s", exc)
        return []


def _same(text: str) -> str:
    return " ".join(text.split()).casefold()


def apply_changes(
    conn: sqlite3.Connection,
    user_id: str,
    add: Sequence[str],
    remove: Sequence[int],
    source_conversation_id: str | None,
) -> None:
    """Remove and add a user's facts in one transaction.

    Only the user's own rows can be removed. An added fact that repeats one
    already kept (ignoring case and spacing) is skipped. Past MAX_FACTS the oldest
    facts are dropped. Any failure leaves the facts as they were.
    """
    conn.execute("BEGIN")
    try:
        for fact_id in remove:
            conn.execute(
                "DELETE FROM user_facts WHERE id = ? AND user_id = ?",
                (fact_id, user_id),
            )
        known = {
            _same(row[0])
            for row in conn.execute(
                "SELECT fact FROM user_facts WHERE user_id = ?", (user_id,)
            )
        }
        learned_at = iso_utc()
        for text in add:
            if _same(text) in known:
                continue
            known.add(_same(text))
            conn.execute(
                "INSERT INTO user_facts "
                "(user_id, fact, learned_at, source_conversation_id) "
                "VALUES (?, ?, ?, ?)",
                (user_id, text, learned_at, source_conversation_id),
            )
        conn.execute(
            "DELETE FROM user_facts WHERE user_id = ? AND id NOT IN ("
            "  SELECT id FROM user_facts WHERE user_id = ? "
            "  ORDER BY learned_at DESC, id DESC LIMIT ?"
            ")",
            (user_id, user_id, MAX_FACTS),
        )
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")


# Limits on what one extraction may change.
MAX_FACT_LENGTH = 200
MAX_ADDS = 10

EXTRACTION_PROMPT = """\
You maintain a short list of lasting facts about a user of a voice assistant, \
such as their name, work, preferences and ongoing goals.

You are given the facts already saved, each with a number, and the latest \
conversation. Decide what to change.

- Use only what the user said. Never save something only the assistant said, \
unless the user confirmed it.
- Prefer lasting facts over one-off topics or questions. Save nothing if the \
user shared nothing about themselves.
- Write each fact as one short sentence about the user.
- Do not repeat a fact that is already saved.
- Remove a saved fact only if the user changed it or took it back. A changed \
fact is a removal of the old one plus an addition of the new one.

Reply with JSON only, in this shape, and nothing else:
{"add": ["fact", ...], "remove": [number, ...]}"""


@dataclass(frozen=True)
class Changes:
    add: list[str]
    remove: list[int]


def parse_changes(reply: str, known_ids: set[int]) -> Changes | None:
    """Read the model's reply; None, with a warning, if it is not usable.

    A fact longer than MAX_FACT_LENGTH is cut. Anything else out of shape means
    the whole reply is refused, so a confused model changes nothing.
    """
    text = reply.strip()
    if text.startswith("```"):  # models often fence JSON despite being told not to
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```")
    try:
        data = json.loads(text)
        if not isinstance(data, dict) or set(data) - {"add", "remove"}:
            raise ValueError("expected an object with 'add' and 'remove'")
        add, remove = data.get("add", []), data.get("remove", [])
        if not isinstance(add, list) or not isinstance(remove, list):
            raise ValueError("'add' and 'remove' must be lists")
        if not all(isinstance(fact, str) and fact.strip() for fact in add):
            raise ValueError("'add' must hold non-empty strings")
        if not all(
            isinstance(n, int) and not isinstance(n, bool) and n in known_ids
            for n in remove
        ):
            raise ValueError("'remove' must hold ids of saved facts")
        if len(add) > MAX_ADDS:
            raise ValueError(f"more than {MAX_ADDS} additions")
    except ValueError as exc:  # includes json.JSONDecodeError
        logger.warning("ignoring fact extraction reply: %s", exc)
        return None
    return Changes(
        add=[" ".join(fact.split())[:MAX_FACT_LENGTH] for fact in add],
        remove=list(dict.fromkeys(remove)),
    )


def session_messages(items, skip_ids: set[str]) -> list[tuple[str, str]]:
    """The (role, text) pairs of a session's user and assistant messages.

    `skip_ids` holds messages carried in from a resumed conversation, which were
    read after the call they belong to.
    """
    messages = []
    for item in items:
        if getattr(item, "type", None) != "message" or item.id in skip_ids:
            continue
        if item.role in ("user", "assistant") and item.text_content:
            messages.append((item.role, item.text_content))
    return messages


async def extract_facts(
    model: llm.LLM, existing: Sequence[Fact], messages: Sequence[tuple[str, str]]
) -> Changes | None:
    """Ask the model what to add to and remove from a user's saved facts.

    None when the model's reply is unusable. Errors from the model propagate.
    """
    saved = "\n".join(f"{fact.id}. {fact.text}" for fact in existing) or "(none)"
    transcript = "\n".join(f"{role}: {text}" for role, text in messages)
    chat_ctx = llm.ChatContext()
    chat_ctx.add_message(role="system", content=EXTRACTION_PROMPT)
    chat_ctx.add_message(
        role="user",
        content=f"Saved facts:\n{saved}\n\nConversation:\n{transcript}",
    )
    response = await model.chat(chat_ctx=chat_ctx).collect()
    return parse_changes(response.text, {fact.id for fact in existing})


# Shutdown callbacks share the worker's shutdown_process_timeout of 10 seconds.
EXTRACTION_TIMEOUT = 6.0


async def update_facts(
    session,
    db_path: str,
    model: llm.LLM,
    user_id: str,
    conversation_id: str,
    carried_ids: set[str],
    timeout: float = EXTRACTION_TIMEOUT,
) -> None:
    """Save what a finished session taught the agent about its user.

    Never raises: a failing or slow model leaves the saved facts as they were.
    """
    try:
        messages = session_messages(session.history.items, carried_ids)
        if not any(role == "user" for role, _ in messages):
            return
        conn = open_db(db_path)
        try:
            existing = load_facts(conn, user_id)
            changes = await asyncio.wait_for(
                extract_facts(model, existing, messages), timeout
            )
            if changes is not None and (changes.add or changes.remove):
                apply_changes(
                    conn, user_id, changes.add, changes.remove, conversation_id
                )
        finally:
            conn.close()
    except asyncio.TimeoutError:
        logger.warning("fact extraction took longer than %s seconds", timeout)
    except Exception:
        logger.exception("could not update the user's facts")


def attach_memory(
    session,
    ctx,
    user_id: str | None,
    conversation_id: str,
    model: llm.LLM,
    carried_ids: set[str] = frozenset(),  # type: ignore[assignment]
) -> bool:
    """Save facts about the user when the job shuts down; True if registered.

    Does nothing without a user id or a history file. Shutdown callbacks run
    concurrently, which is fine: this reads the session's own history, not the
    rows the recorder writes.
    """
    path = db_path_from_env()
    if not user_id or path is None:
        return False

    async def _remember() -> None:
        await update_facts(session, path, model, user_id, conversation_id, carried_ids)

    ctx.add_shutdown_callback(_remember)
    return True
