import json
import logging
import sqlite3
from types import SimpleNamespace

import pytest

from memory import (
    EXTRACTION_PROMPT,
    MAX_FACT_LENGTH,
    MAX_FACTS,
    Changes,
    Fact,
    apply_changes,
    extract_facts,
    load_facts,
    parse_user,
    session_messages,
)
from recorder import open_db


def test_parse_user_reads_the_id():
    assert parse_user('{"user":"u-1"}') == "u-1"


def test_parse_user_reads_the_id_beside_other_keys():
    meta = '{"persona":"tutor","user":"u-1","resume":{"conversation_id":"c","mode":"fork"}}'
    assert parse_user(meta) == "u-1"


@pytest.mark.parametrize(
    "metadata",
    [None, "", "   ", "not json", "[]", '{"persona":"tutor"}'],
)
def test_parse_user_absent_is_silently_none(metadata, caplog):
    with caplog.at_level(logging.WARNING, logger="memory"):
        assert parse_user(metadata) is None
    assert caplog.records == []


@pytest.mark.parametrize("metadata", ['{"user":""}', '{"user":7}', '{"user":null}'])
def test_parse_user_unusable_is_ignored_with_a_warning(metadata, caplog):
    with caplog.at_level(logging.WARNING, logger="memory"):
        assert parse_user(metadata) is None
    assert len(caplog.records) == 1


def _conn(tmp_path):
    return open_db(str(tmp_path / "history.db"))


def _texts(conn, user_id="u-1"):
    return [fact.text for fact in load_facts(conn, user_id)]


def test_new_file_has_the_facts_table(tmp_path):
    conn = _conn(tmp_path)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master")}
    assert {"user_facts", "user_facts_user_id"} <= tables


def test_old_file_gains_the_facts_table(tmp_path):
    path = str(tmp_path / "history.db")
    old = sqlite3.connect(path)
    old.execute("CREATE TABLE conversations (id TEXT PRIMARY KEY, started_at TEXT)")
    old.commit()
    old.close()

    conn = open_db(path)

    assert load_facts(conn, "u-1") == []


def test_add_keeps_date_and_source(tmp_path):
    conn = _conn(tmp_path)

    apply_changes(conn, "u-1", ["Is a nurse"], [], "room-1")

    [fact] = load_facts(conn, "u-1")
    assert fact.text == "Is a nurse"
    assert fact.source_conversation_id == "room-1"
    assert fact.learned_at.endswith("Z")


def test_facts_are_kept_per_user(tmp_path):
    conn = _conn(tmp_path)
    apply_changes(conn, "u-1", ["Likes tea"], [], None)
    apply_changes(conn, "u-2", ["Likes coffee"], [], None)

    assert _texts(conn, "u-1") == ["Likes tea"]
    assert _texts(conn, "u-2") == ["Likes coffee"]


def test_remove_deletes_the_named_fact(tmp_path):
    conn = _conn(tmp_path)
    apply_changes(conn, "u-1", ["Likes tea", "Is a nurse"], [], None)
    tea = load_facts(conn, "u-1")[0]

    apply_changes(conn, "u-1", [], [tea.id], None)

    assert _texts(conn) == ["Is a nurse"]


def test_remove_cannot_touch_another_users_fact(tmp_path):
    conn = _conn(tmp_path)
    apply_changes(conn, "u-2", ["Likes coffee"], [], None)
    other = load_facts(conn, "u-2")[0]

    apply_changes(conn, "u-1", [], [other.id], None)

    assert _texts(conn, "u-2") == ["Likes coffee"]


def test_a_changed_fact_is_a_remove_plus_an_add(tmp_path):
    conn = _conn(tmp_path)
    apply_changes(conn, "u-1", ["Works as a nurse"], [], None)
    old = load_facts(conn, "u-1")[0]

    apply_changes(conn, "u-1", ["Works as a teacher"], [old.id], None)

    assert _texts(conn) == ["Works as a teacher"]


def test_duplicate_text_is_not_saved_twice(tmp_path):
    conn = _conn(tmp_path)
    apply_changes(conn, "u-1", ["Likes tea"], [], None)

    apply_changes(conn, "u-1", ["  likes   TEA ", "Likes tea"], [], None)

    assert _texts(conn) == ["Likes tea"]


def test_duplicates_within_one_call_are_saved_once(tmp_path):
    conn = _conn(tmp_path)

    apply_changes(conn, "u-1", ["Likes tea", "likes tea"], [], None)

    assert _texts(conn) == ["Likes tea"]


def test_removing_and_re_adding_the_same_text_keeps_it(tmp_path):
    conn = _conn(tmp_path)
    apply_changes(conn, "u-1", ["Likes tea"], [], None)
    old = load_facts(conn, "u-1")[0]

    apply_changes(conn, "u-1", ["Likes tea"], [old.id], None)

    assert _texts(conn) == ["Likes tea"]


def test_oldest_facts_are_dropped_beyond_the_cap(tmp_path):
    conn = _conn(tmp_path)
    apply_changes(conn, "u-1", [f"fact {n}" for n in range(MAX_FACTS)], [], None)

    apply_changes(conn, "u-1", ["newest", "newer still"], [], None)

    texts = _texts(conn)
    assert len(texts) == MAX_FACTS
    assert texts[:2] == ["fact 2", "fact 3"]
    assert texts[-2:] == ["newest", "newer still"]


def test_the_cap_is_per_user(tmp_path):
    conn = _conn(tmp_path)
    apply_changes(conn, "u-2", ["Likes coffee"], [], None)

    apply_changes(conn, "u-1", [f"fact {n}" for n in range(MAX_FACTS + 5)], [], None)

    assert len(_texts(conn, "u-1")) == MAX_FACTS
    assert _texts(conn, "u-2") == ["Likes coffee"]


def test_a_failing_write_rolls_everything_back(tmp_path):
    conn = _conn(tmp_path)
    apply_changes(conn, "u-1", ["Likes tea"], [], None)
    tea = load_facts(conn, "u-1")[0]

    conn.execute(
        "CREATE TRIGGER refuse BEFORE INSERT ON user_facts WHEN NEW.fact = 'boom' "
        "BEGIN SELECT RAISE(ABORT, 'refused'); END"
    )

    with pytest.raises(sqlite3.DatabaseError):
        # The removal and the first add have run when the second add is refused.
        apply_changes(conn, "u-1", ["Is a nurse", "boom"], [tea.id], None)

    assert _texts(conn) == ["Likes tea"]
    assert not conn.in_transaction


class _FakeStream:
    def __init__(self, text):
        self._text = text

    async def collect(self):
        return SimpleNamespace(text=self._text)


class _FakeLLM:
    def __init__(self, text):
        self.text = text
        self.contexts = []

    def chat(self, *, chat_ctx):
        self.contexts.append(chat_ctx)
        return _FakeStream(self.text)


def _facts(*texts):
    return [
        Fact(n, text, "2026-01-01T00:00:00.000Z", None)
        for n, text in enumerate(texts, 1)
    ]


async def test_extract_facts_reads_a_valid_reply():
    model = _FakeLLM('{"add": ["Is a nurse"], "remove": [1]}')

    changes = await extract_facts(model, _facts("Likes tea"), [("user", "I'm a nurse")])

    assert changes == Changes(add=["Is a nurse"], remove=[1])


async def test_extract_facts_prompt_holds_numbered_facts_and_the_transcript():
    model = _FakeLLM('{"add": [], "remove": []}')

    await extract_facts(
        model, _facts("Likes tea"), [("user", "hello"), ("assistant", "hi")]
    )

    [ctx] = model.contexts
    system, user = ctx.messages()
    assert system.text_content == EXTRACTION_PROMPT
    assert "1. Likes tea" in user.text_content
    assert "user: hello\nassistant: hi" in user.text_content


async def test_extract_facts_prompt_without_facts_says_none():
    model = _FakeLLM('{"add": [], "remove": []}')

    await extract_facts(model, [], [("user", "hello")])

    assert "(none)" in model.contexts[0].messages()[1].text_content


@pytest.mark.parametrize(
    "reply",
    [
        "not json",
        "[]",
        '"add"',
        '{"add": "Is a nurse", "remove": []}',
        '{"add": [3], "remove": []}',
        '{"add": [""], "remove": []}',
        '{"add": [], "remove": ["1"]}',
        '{"add": [], "remove": [true]}',
        '{"add": [], "remove": [99]}',
        '{"add": [], "remove": [], "extra": 1}',
        '{"add": ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k"]}',
    ],
)
async def test_extract_facts_refuses_unusable_replies(reply, caplog):
    model = _FakeLLM(reply)

    with caplog.at_level(logging.WARNING, logger="memory"):
        assert await extract_facts(model, _facts("Likes tea"), [("user", "x")]) is None
    assert len(caplog.records) == 1


async def test_extract_facts_accepts_ten_additions_and_missing_keys():
    ten = ", ".join(f'"fact {n}"' for n in range(10))

    assert len((await extract_facts(_FakeLLM(f'{{"add": [{ten}]}}'), [], [])).add) == 10
    assert await extract_facts(_FakeLLM("{}"), [], []) == Changes([], [])


async def test_extract_facts_cuts_long_facts_and_flattens_lines():
    long = "x" * 500
    model = _FakeLLM(json.dumps({"add": [long, "two\nlines  here"], "remove": []}))

    changes = await extract_facts(model, [], [("user", "x")])

    assert changes.add == ["x" * MAX_FACT_LENGTH, "two lines here"]


async def test_extract_facts_accepts_a_fenced_reply_and_dedupes_removals():
    model = _FakeLLM('```json\n{"add": [], "remove": [1, 1]}\n```')

    assert await extract_facts(model, _facts("a"), []) == Changes([], [1])


async def test_extract_facts_lets_model_errors_propagate():
    class Broken:
        def chat(self, *, chat_ctx):
            raise RuntimeError("down")

    with pytest.raises(RuntimeError):
        await extract_facts(Broken(), [], [("user", "x")])


def _item(item_id, role, text, kind="message"):
    return SimpleNamespace(id=item_id, type=kind, role=role, text_content=text)


def test_session_messages_skips_carried_empty_and_other_items():
    items = [
        _item("c1:0", "user", "old"),
        _item("m1", "user", "I'm a nurse"),
        _item("m2", "assistant", "Nice"),
        _item("m3", "assistant", ""),
        _item("m4", "system", "rules"),
        _item("f1", "assistant", "x", kind="function_call"),
    ]

    assert session_messages(items, {"c1:0"}) == [
        ("user", "I'm a nurse"),
        ("assistant", "Nice"),
    ]
