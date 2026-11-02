import sqlite3
from types import SimpleNamespace

import pytest

from recorder import (
    RESUME_WINDOW,
    CarriedMessage,
    Recorder,
    ResumeError,
    ResumeRequest,
    attach,
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


def test_fork_copies_carried_messages_and_leaves_source(tmp_path):
    conn = open_db(str(tmp_path / "history.db"))
    _seed(conn, "c1", [("user", "hello"), ("assistant", "hi there")])
    source_before = conn.execute(
        "SELECT * FROM messages WHERE conversation_id = 'c1' ORDER BY id"
    ).fetchall()
    carried = load_resume(conn, ResumeRequest("c1", "fork"))

    start_conversation(conn, "room-2", "a", parent_id="c1", copy_messages=carried)

    copied = conn.execute(
        "SELECT id, role, content, created_at, interrupted FROM messages "
        "WHERE conversation_id = 'room-2' ORDER BY id"
    ).fetchall()
    assert copied == [
        ("room-2:0", "user", "hello", carried[0].created_at, 0),
        ("room-2:1", "assistant", "hi there", carried[1].created_at, 0),
    ]
    assert (
        conn.execute(
            "SELECT * FROM messages WHERE conversation_id = 'c1' ORDER BY id"
        ).fetchall()
        == source_before
    )
    assert _conversation(conn, "c1")[1:] == (None, None)


def test_failed_fork_leaves_nothing_behind(tmp_path):
    conn = open_db(str(tmp_path / "history.db"))
    good = CarriedMessage("m0", "user", "ok", "2026-01-01T00:00:00.000Z", False)
    bad = CarriedMessage("m1", "user", None, "2026-01-01T00:00:01.000Z", False)

    with pytest.raises(sqlite3.IntegrityError):
        start_conversation(
            conn, "room-2", "a", parent_id="c1", copy_messages=[good, bad]
        )

    assert _conversation(conn, "room-2") is None
    assert conn.execute("SELECT COUNT(*) FROM messages").fetchone() == (0,)


class _FakeSession:
    def __init__(self, items):
        self.history = SimpleNamespace(items=items)
        self.handlers = {}

    def on(self, name):
        def register(fn):
            self.handlers[name] = fn
            return fn

        return register


class _FakeCtx:
    def __init__(self, room_name):
        self.room = SimpleNamespace(name=room_name)
        self.shutdown_callbacks = []

    def add_shutdown_callback(self, fn):
        self.shutdown_callbacks.append(fn)


def _item(item_id, role, text, created_at):
    return SimpleNamespace(
        type="message",
        id=item_id,
        role=role,
        text_content=text,
        created_at=created_at,
        interrupted=False,
    )


def _message_rows(conn, conversation_id):
    return conn.execute(
        "SELECT id, role, content FROM messages WHERE conversation_id = ? "
        "ORDER BY created_at, id",
        (conversation_id,),
    ).fetchall()


@pytest.mark.parametrize("mode", ["continue", "fork"])
def test_attach_resume_skips_seeded_items_on_close(tmp_path, monkeypatch, mode):
    path = str(tmp_path / "history.db")
    monkeypatch.setenv("CHAT_DB_PATH", path)
    conn = open_db(path)
    _seed(conn, "c1", [("user", "hello"), ("assistant", "hi there")])
    request = ResumeRequest("c1", mode)
    carried = load_resume(conn, request)
    seeded = [
        _item(m.id, m.role, m.content, 1_800_000_000.0 + n)
        for n, m in enumerate(carried)
    ]
    new = _item("new-1", "user", "and now?", 1_800_000_100.0)
    session = _FakeSession([*seeded, new])
    ctx = _FakeCtx("room-2")

    attach(session, ctx, "a", request, carried)
    session.handlers["close"](None)

    target = "c1" if mode == "continue" else "room-2"
    rows = _message_rows(conn, target)
    assert ("new-1", "user", "and now?") in rows
    if mode == "continue":
        # Seeded rows are untouched, not rewritten or duplicated.
        assert rows == [
            ("c1:0", "user", "hello"),
            ("c1:1", "assistant", "hi there"),
            ("new-1", "user", "and now?"),
        ]
        assert _conversation(conn, "c1")[1] is not None
    else:
        # The copy holds the seeded text once, under the fork's own ids.
        assert rows == [
            ("room-2:0", "user", "hello"),
            ("room-2:1", "assistant", "hi there"),
            ("new-1", "user", "and now?"),
        ]
        assert _conversation(conn, "room-2")[2] == "c1"
        assert _message_rows(conn, "c1") == [
            ("c1:0", "user", "hello"),
            ("c1:1", "assistant", "hi there"),
        ]
