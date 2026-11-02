"""Facts the agent remembers about a user across calls.

See docs/conversation-storage.md for the table this module reads and writes.
"""

import json
import logging
import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass

from recorder import iso_utc

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
