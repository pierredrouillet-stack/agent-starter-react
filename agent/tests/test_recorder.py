import sqlite3

import pytest

from recorder import (
    RESUME_WINDOW,
    Recorder,
    ResumeError,
    ResumeRequest,
    load_resume,
    open_db,
    parse_resume,
    start_conversation,
)

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


def _seed(conn, conversation_id, messages):
    conn.execute(
        "INSERT INTO conversations (id, started_at) VALUES (?, '2026-01-01T00:00:00.000Z')",
        (conversation_id,),
    )
    for i, (role, content) in enumerate(messages):
        conn.execute(
            "INSERT INTO messages VALUES (?, ?, ?, ?, ?, 0)",
            (
                f"{conversation_id}:{i}",
                conversation_id,
                role,
                content,
                f"2026-01-01T00:{i // 60:02d}:{i % 60:02d}.000Z",
            ),
        )


def test_load_resume_orders_oldest_first_and_skips_other_roles(tmp_path):
    conn = open_db(str(tmp_path / "history.db"))
    _seed(
        conn,
        "c1",
        [("user", "one"), ("system", "ignored"), ("assistant", "two"), ("user", "3")],
    )
    _seed(conn, "c2", [("user", "other conversation")])

    loaded = load_resume(conn, ResumeRequest("c1", "continue"))

    assert [(m.role, m.content) for m in loaded] == [
        ("user", "one"),
        ("assistant", "two"),
        ("user", "3"),
    ]


def test_load_resume_keeps_only_latest_100(tmp_path):
    conn = open_db(str(tmp_path / "history.db"))
    _seed(conn, "c1", [("user", str(n)) for n in range(130)])

    loaded = load_resume(conn, ResumeRequest("c1", "fork"))

    assert len(loaded) == RESUME_WINDOW
    assert loaded[0].content == "30"
    assert loaded[-1].content == "129"


def test_load_resume_unknown_conversation(tmp_path):
    conn = open_db(str(tmp_path / "history.db"))
    with pytest.raises(ResumeError):
        load_resume(conn, ResumeRequest("missing", "continue"))


def test_load_resume_empty_conversation(tmp_path):
    conn = open_db(str(tmp_path / "history.db"))
    _seed(conn, "c1", [("system", "only a system note")])
    with pytest.raises(ResumeError):
        load_resume(conn, ResumeRequest("c1", "continue"))


def _conversation(conn, conversation_id):
    return conn.execute(
        "SELECT started_at, ended_at, parent_id FROM conversations WHERE id = ?",
        (conversation_id,),
    ).fetchone()


def test_continue_clears_ended_at_and_keeps_started_at(tmp_path):
    conn = open_db(str(tmp_path / "history.db"))
    conn.execute(
        "INSERT INTO conversations (id, started_at, ended_at, agent_name) "
        "VALUES ('c1', '2026-01-01T00:00:00.000Z', '2026-01-01T01:00:00.000Z', 'a')"
    )

    start_conversation(conn, "c1", "a")

    assert _conversation(conn, "c1") == ("2026-01-01T00:00:00.000Z", None, None)


def test_fork_writes_parent_id(tmp_path):
    conn = open_db(str(tmp_path / "history.db"))

    start_conversation(conn, "room-2", "a", parent_id="c1")

    _, ended_at, parent_id = _conversation(conn, "room-2")
    assert ended_at is None
    assert parent_id == "c1"


def test_recorder_passes_parent_id(tmp_path, monkeypatch):
    path = str(tmp_path / "history.db")
    monkeypatch.setenv("CHAT_DB_PATH", path)

    Recorder("room-2", "a", parent_id="c1").start()

    assert _conversation(open_db(path), "room-2")[2] == "c1"
