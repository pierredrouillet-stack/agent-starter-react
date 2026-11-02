import sqlite3

import pytest

from recorder import ResumeRequest, open_db, parse_resume

OLD_SCHEMA = """
CREATE TABLE conversations (
  id          TEXT PRIMARY KEY,
  started_at  TEXT NOT NULL,
  ended_at    TEXT,
  agent_name  TEXT
);

CREATE TABLE messages (
  id               TEXT PRIMARY KEY,
  conversation_id  TEXT NOT NULL REFERENCES conversations(id),
  role             TEXT NOT NULL,
  content          TEXT NOT NULL,
  created_at       TEXT NOT NULL,
  interrupted      INTEGER NOT NULL DEFAULT 0
);
"""


def _columns(conn: sqlite3.Connection) -> set[str]:
    return {row[1] for row in conn.execute("PRAGMA table_info(conversations)")}


def test_new_file_has_parent_id(tmp_path):
    conn = open_db(str(tmp_path / "history.db"))
    assert "parent_id" in _columns(conn)


def test_old_file_gains_parent_id_and_keeps_rows(tmp_path):
    path = str(tmp_path / "history.db")
    old = sqlite3.connect(path)
    old.executescript(OLD_SCHEMA)
    old.execute(
        "INSERT INTO conversations VALUES ('c1', '2026-01-01T00:00:00.000Z', NULL, 'a')"
    )
    old.execute(
        "INSERT INTO messages VALUES "
        "('m1', 'c1', 'user', 'hi', '2026-01-01T00:00:01.000Z', 0)"
    )
    old.commit()
    old.close()

    conn = open_db(path)

    assert "parent_id" in _columns(conn)
    assert conn.execute("SELECT id, parent_id FROM conversations").fetchall() == [
        ("c1", None)
    ]
    assert conn.execute("SELECT id, content FROM messages").fetchall() == [("m1", "hi")]
    # Opening again is a no-op rather than a duplicate-column error.
    open_db(path)


def test_parse_resume_valid():
    for mode in ("continue", "fork"):
        meta = f'{{"resume":{{"conversation_id":"room-1","mode":"{mode}"}}}}'
        assert parse_resume(meta) == ResumeRequest("room-1", mode)


@pytest.mark.parametrize(
    "metadata",
    [
        None,
        "",
        "   ",
        "not json",
        "[]",
        '{"resume":{"mode":"continue"}}',
        '{"resume":{"conversation_id":"","mode":"continue"}}',
        '{"resume":{"conversation_id":"c1","mode":"rewind"}}',
        '{"resume":{"conversation_id":"c1","mode":"fork","extra":1}}',
        '{"resume":{"conversation_id":"c1","mode":"fork"},"other":1}',
        '{"resume":"c1"}',
    ],
)
def test_parse_resume_rejects(metadata):
    assert parse_resume(metadata) is None
