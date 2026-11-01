"""Saves agent sessions to the shared history SQLite file.

See docs/conversation-storage.md for the schema this module writes.
"""

import logging
import os
import sqlite3
from datetime import datetime, timezone

logger = logging.getLogger("recorder")

_warned_unset = False

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
  id          TEXT PRIMARY KEY,
  started_at  TEXT NOT NULL,
  ended_at    TEXT,
  agent_name  TEXT
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


def iso_utc(epoch: float | None = None) -> str:
    moment = (
        datetime.now(timezone.utc)
        if epoch is None
        else datetime.fromtimestamp(epoch, timezone.utc)
    )
    return moment.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def open_db(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=5.0, isolation_level=None)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.executescript(SCHEMA)
    return conn


def start_conversation(
    conn: sqlite3.Connection, conversation_id: str, agent_name: str | None
) -> None:
    conn.execute(
        "INSERT INTO conversations (id, started_at, ended_at, agent_name) "
        "VALUES (?, ?, NULL, ?) "
        "ON CONFLICT(id) DO UPDATE SET ended_at = NULL, agent_name = excluded.agent_name",
        (conversation_id, iso_utc(), agent_name),
    )


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

    def __init__(self, conversation_id: str, agent_name: str | None) -> None:
        self.conversation_id = conversation_id
        self.agent_name = agent_name
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
        self._run(start_conversation, self.conversation_id, self.agent_name)

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
