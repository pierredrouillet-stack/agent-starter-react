"""Saves agent sessions to the shared history SQLite file.

See docs/conversation-storage.md for the schema this module writes.
"""

import json
import logging
import os
import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone

logger = logging.getLogger("recorder")

_warned_unset = False

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
  id          TEXT PRIMARY KEY,
  started_at  TEXT NOT NULL,
  ended_at    TEXT,
  agent_name  TEXT,
  parent_id   TEXT
);

CREATE TABLE IF NOT EXISTS messages (
  id               TEXT PRIMARY KEY,
  conversation_id  TEXT NOT NULL REFERENCES conversations(id),
  role             TEXT NOT NULL,
  content          TEXT NOT NULL,
  created_at       TEXT NOT NULL,
  interrupted      INTEGER NOT NULL DEFAULT 0
);
"""


@dataclass(frozen=True)
class ResumeRequest:
    conversation_id: str
    mode: str  # "continue" or "fork"


def parse_resume(metadata: str | None) -> ResumeRequest | None:
    """Read a resume request from job metadata; None if absent or unusable."""
    if not metadata or not metadata.strip():
        return None
    try:
        data = json.loads(metadata)
        if not isinstance(data, dict):
            raise ValueError("expected a JSON object")
        # A persona id rides in the same metadata but is read by parse_persona.
        keys = set(data) - {"persona"}
        if not keys:
            return None
        if keys != {"resume"}:
            raise ValueError("expected only 'resume' and 'persona' keys")
        body = data["resume"]
        if not isinstance(body, dict) or set(body) != {"conversation_id", "mode"}:
            raise ValueError("'resume' needs exactly conversation_id and mode")
        conversation_id, mode = body["conversation_id"], body["mode"]
        if not isinstance(conversation_id, str) or not conversation_id:
            raise ValueError("conversation_id must be a non-empty string")
        if mode not in ("continue", "fork"):
            raise ValueError(f"unknown mode {mode!r}")
    except ValueError as exc:  # includes json.JSONDecodeError
        logger.warning("ignoring resume request: %s", exc)
        return None
    return ResumeRequest(conversation_id, mode)


# How many of a conversation's latest messages are carried into a resumed session.
RESUME_WINDOW = 100


class ResumeError(Exception):
    """The requested conversation cannot be resumed."""


@dataclass(frozen=True)
class CarriedMessage:
    id: str
    role: str
    content: str
    created_at: str
    interrupted: bool


def load_resume(
    conn: sqlite3.Connection, request: ResumeRequest
) -> list[CarriedMessage]:
    """Latest user and assistant messages of the source conversation, oldest first."""
    exists = conn.execute(
        "SELECT 1 FROM conversations WHERE id = ?", (request.conversation_id,)
    ).fetchone()
    if exists is None:
        raise ResumeError(f"unknown conversation {request.conversation_id!r}")
    rows = conn.execute(
        "SELECT id, role, content, created_at, interrupted FROM ("
        "  SELECT rowid AS rid, * FROM messages "
        "  WHERE conversation_id = ? AND role IN ('user', 'assistant') "
        "  ORDER BY created_at DESC, rid DESC LIMIT ?"
        ") ORDER BY created_at, rid",
        (request.conversation_id, RESUME_WINDOW),
    ).fetchall()
    if not rows:
        raise ResumeError(f"conversation {request.conversation_id!r} has no messages")
    return [CarriedMessage(r[0], r[1], r[2], r[3], bool(r[4])) for r in rows]


def iso_utc(epoch: float | None = None) -> str:
    moment = (
        datetime.now(timezone.utc)
        if epoch is None
        else datetime.fromtimestamp(epoch, timezone.utc)
    )
    return moment.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def open_db(path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    conn = sqlite3.connect(path, timeout=5.0, isolation_level=None)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.executescript(SCHEMA)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(conversations)")}
    if "parent_id" not in columns:
        conn.execute("ALTER TABLE conversations ADD COLUMN parent_id TEXT")
    return conn


def start_conversation(
    conn: sqlite3.Connection,
    conversation_id: str,
    agent_name: str | None,
    parent_id: str | None = None,
    copy_messages: Sequence[CarriedMessage] = (),
) -> None:
    """Upsert the conversation row; `copy_messages` land in the same transaction.

    Copies get the ids `<conversation_id>:<n>` since message ids are unique.
    """
    conn.execute("BEGIN")
    try:
        # On conflict (a continued conversation) started_at and parent_id are kept.
        conn.execute(
            "INSERT INTO conversations "
            "(id, started_at, ended_at, agent_name, parent_id) "
            "VALUES (?, ?, NULL, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET ended_at = NULL, "
            "agent_name = excluded.agent_name",
            (conversation_id, iso_utc(), agent_name, parent_id),
        )
        for n, message in enumerate(copy_messages):
            conn.execute(
                "INSERT INTO messages "
                "(id, conversation_id, role, content, created_at, interrupted) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    f"{conversation_id}:{n}",
                    conversation_id,
                    message.role,
                    message.content,
                    message.created_at,
                    int(message.interrupted),
                ),
            )
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")


def upsert_message(
    conn: sqlite3.Connection,
    conversation_id: str,
    message_id: str,
    role: str,
    content: str,
    created_at: float,
    interrupted: bool,
) -> None:
    conn.execute(
        "INSERT INTO messages (id, conversation_id, role, content, created_at, interrupted) "
        "VALUES (?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(id) DO UPDATE SET content = excluded.content, "
        "interrupted = excluded.interrupted",
        (
            message_id,
            conversation_id,
            role,
            content,
            iso_utc(created_at),
            int(interrupted),
        ),
    )


def end_conversation(conn: sqlite3.Connection, conversation_id: str) -> None:
    conn.execute(
        "UPDATE conversations SET ended_at = ? WHERE id = ?",
        (iso_utc(), conversation_id),
    )


def db_path_from_env() -> str | None:
    return os.environ.get("CHAT_DB_PATH") or None


class Recorder:
    """Writes one conversation. Every method logs and swallows errors."""

    def __init__(
        self,
        conversation_id: str,
        agent_name: str | None,
        parent_id: str | None = None,
        copy_messages: Sequence[CarriedMessage] = (),
    ) -> None:
        self.conversation_id = conversation_id
        self.agent_name = agent_name
        self.parent_id = parent_id
        self.copy_messages = copy_messages
        self._conn: sqlite3.Connection | None = None
        self._enabled = False
        path = db_path_from_env()
        if path is None:
            global _warned_unset
            if not _warned_unset:
                logger.warning("CHAT_DB_PATH is not set; conversation recording is off")
                _warned_unset = True
            return
        try:
            self._conn = open_db(path)
            self._enabled = True
        except Exception:
            logger.exception("could not open history database at %s", path)

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _run(self, fn, *args) -> None:
        if not self._enabled or self._conn is None:
            return
        try:
            fn(self._conn, *args)
        except Exception:
            logger.exception("history write failed")

    def start(self) -> None:
        self._run(
            start_conversation,
            self.conversation_id,
            self.agent_name,
            self.parent_id,
            self.copy_messages,
        )

    def save_message(
        self,
        message_id: str,
        role: str,
        content: str,
        created_at: float,
        interrupted: bool,
    ) -> None:
        self._run(
            upsert_message,
            self.conversation_id,
            message_id,
            role,
            content,
            created_at,
            interrupted,
        )

    def end(self) -> None:
        self._run(end_conversation, self.conversation_id)


def attach(
    session,
    ctx,
    agent_name: str | None,
    resume: ResumeRequest | None = None,
    carried: Sequence[CarriedMessage] = (),
) -> Recorder:
    """Record `session` to the history file. Call before `session.start`.

    With `resume`, a continued conversation is recorded under its original id and
    a forked one under the room name, with `carried` copied into it. `carried`
    must be what seeded the session's chat context, under the same message ids.
    """
    if resume is not None and resume.mode == "continue":
        recorder = Recorder(resume.conversation_id, agent_name)
    elif resume is not None:
        recorder = Recorder(
            ctx.room.name,
            agent_name,
            parent_id=resume.conversation_id,
            copy_messages=carried,
        )
    else:
        recorder = Recorder(ctx.room.name, agent_name)
    # Seeded items sit in session.history but are already stored; skip them on close.
    saved: set[str] = {message.id for message in carried}
    ended = False

    def save_item(item) -> None:
        if getattr(item, "type", None) != "message":
            return
        if item.role not in ("user", "assistant"):
            return
        text = item.text_content
        if not text:
            return
        recorder.save_message(
            item.id, item.role, text, item.created_at, bool(item.interrupted)
        )
        saved.add(item.id)

    def finish() -> None:
        nonlocal ended
        if ended:
            return
        ended = True
        try:
            for item in session.history.items:
                if getattr(item, "id", None) not in saved:
                    save_item(item)
        except Exception:
            logger.exception("could not reconcile session history")
        recorder.end()

    @session.on("conversation_item_added")
    def _on_item(event) -> None:
        save_item(event.item)

    @session.on("close")
    def _on_close(event) -> None:
        finish()

    async def _on_shutdown() -> None:
        finish()

    ctx.add_shutdown_callback(_on_shutdown)
    recorder.start()
    return recorder
