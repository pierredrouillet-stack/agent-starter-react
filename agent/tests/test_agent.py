# Agent behavior is covered by the simulations in scenarios.yaml, which run full
# conversations against the agent on LiveKit Cloud (see README.md). The eval
# below is kept as an example of the in-process testing framework
# (https://docs.livekit.io/agents/start/testing/) for turn-level checks that
# don't need a live session. Uncomment it and run `uv run pytest` to use it.
#
# import textwrap
#
# import pytest
# from livekit.agents import AgentSession, inference, llm
#
# from agent import Assistant
#
#
# def _judge_llm() -> llm.LLM:
#     return inference.LLM(model="openai/gpt-4.1-mini")
#
#
# @pytest.mark.asyncio
# async def test_offers_assistance() -> None:
#     """Evaluation of the agent's friendly nature."""
#     async with (
#         _judge_llm() as judge_llm,
#         AgentSession() as session,
#     ):
#         await session.start(Assistant())
#
#         # Run an agent turn following the user's greeting
#         result = await session.run(user_input="Hello")
#
#         # Evaluate the agent's response for friendliness
#         await (
#             result.expect.next_event()
#             .is_message(role="assistant")
#             .judge(
#                 judge_llm,
#                 intent=textwrap.dedent(
#                     """\
#                     Greets the user in a friendly manner.
#
#                     Optional context that may or may not be included:
#                     - Offer of assistance with any request the user may have
#                     - Other small talk or chit chat is acceptable, so long as it is friendly and not too intrusive
#                     """
#                 ),
#             )
#         )
#
#         # Ensures there are no function calls or other unexpected events
#         result.expect.no_more_events()


import json
import logging
from dataclasses import replace

import pytest

from agent import (
    RESUME_WELCOME,
    Assistant,
    carried_chat_ctx,
    greet,
    resolve_resume,
    session_persona,
)
from memory import apply_changes, load_user_facts, parse_user
from personas import DEFAULT_PERSONA, PERSONAS
from recorder import ResumeRequest, open_db


@pytest.fixture
def history(tmp_path, monkeypatch):
    path = str(tmp_path / "history.db")
    monkeypatch.setenv("CHAT_DB_PATH", path)
    conn = open_db(path)
    conn.execute(
        "INSERT INTO conversations (id, started_at) VALUES ('c1', '2026-01-01T00:00:00Z')"
    )
    conn.execute(
        "INSERT INTO messages VALUES "
        "('m1', 'c1', 'user', 'hello', '2026-01-01T00:00:01Z', 0), "
        "('m2', 'c1', 'assistant', 'hi there', '2026-01-01T00:00:02Z', 1)"
    )
    return conn


def _meta(conversation_id, mode="continue"):
    return json.dumps({"resume": {"conversation_id": conversation_id, "mode": mode}})


@pytest.mark.parametrize(
    "metadata",
    [None, "", "not json", '{"resume":{"conversation_id":"c1","mode":"rewind"}}'],
)
def test_malformed_metadata_is_an_ordinary_session(history, metadata):
    assert resolve_resume(metadata) == (None, [])


def test_unknown_conversation_is_an_ordinary_session(history):
    assert resolve_resume(_meta("missing")) == (None, [])


def test_unset_history_path_is_an_ordinary_session(history, monkeypatch):
    monkeypatch.delenv("CHAT_DB_PATH")
    assert resolve_resume(_meta("c1")) == (None, [])


def test_valid_request_carries_messages(history):
    request, carried = resolve_resume(_meta("c1", "fork"))

    assert (request.conversation_id, request.mode) == ("c1", "fork")
    assert [(m.id, m.content) for m in carried] == [("m1", "hello"), ("m2", "hi there")]

    chat_ctx = carried_chat_ctx(carried)
    assert [(i.id, i.role, i.text_content, i.interrupted) for i in chat_ctx.items] == [
        ("m1", "user", "hello", False),
        ("m2", "assistant", "hi there", True),
    ]


def _with_persona(history, persona):
    history.execute("UPDATE conversations SET persona = ? WHERE id = 'c1'", (persona,))


@pytest.mark.parametrize("mode", ["continue", "fork"])
def test_resumed_session_keeps_the_saved_persona(history, mode):
    _with_persona(history, "tutor")
    metadata = json.dumps(
        {
            "persona": "storyteller",
            "resume": {"conversation_id": "c1", "mode": mode},
        }
    )
    request, _ = resolve_resume(metadata)

    assert session_persona(metadata, request) is PERSONAS["tutor"]


def test_conversation_saved_without_persona_runs_default_silently(history, caplog):
    metadata = json.dumps(
        {"persona": "tutor", "resume": {"conversation_id": "c1", "mode": "continue"}}
    )
    request, _ = resolve_resume(metadata)

    with caplog.at_level(logging.WARNING):
        assert session_persona(metadata, request) is DEFAULT_PERSONA
    assert caplog.records == []


def test_saved_persona_that_no_longer_exists_runs_default_and_warns(history, caplog):
    _with_persona(history, "retired")
    request = ResumeRequest("c1", "continue")

    with caplog.at_level(logging.WARNING, logger="personas"):
        assert session_persona(None, request) is DEFAULT_PERSONA
    assert "retired" in caplog.text


def test_session_without_resume_uses_the_metadata_persona(history):
    assert session_persona('{"persona": "tutor"}', None) is PERSONAS["tutor"]
    assert session_persona(None, None) is DEFAULT_PERSONA


def _remember(history, user_id, *facts):
    apply_changes(history, user_id, list(facts), [], "c1")


def test_user_facts_reach_every_persona(history):
    _remember(history, "u-1", "Is a nurse", "Prefers short answers")
    facts = load_user_facts("u-1")

    for persona in PERSONAS.values():
        instructions = Assistant(persona, facts=facts).instructions
        assert "Is a nurse" in instructions
        assert "Prefers short answers" in instructions
        assert "# What you know about the user" in instructions


def test_facts_reach_a_resumed_session(history):
    _remember(history, "u-1", "Is a nurse")
    metadata = json.dumps(
        {"user": "u-1", "resume": {"conversation_id": "c1", "mode": "continue"}}
    )
    request, carried = resolve_resume(metadata)

    assistant = Assistant(
        DEFAULT_PERSONA,
        carried_chat_ctx(carried),
        load_user_facts(parse_user(metadata)),
    )

    assert request is not None
    assert "Is a nurse" in assistant.instructions


def test_only_the_users_own_facts_are_loaded(history):
    _remember(history, "u-1", "Is a nurse")
    _remember(history, "u-2", "Is a pilot")

    assert [f.text for f in load_user_facts("u-1")] == ["Is a nurse"]


@pytest.mark.parametrize("user_id", [None, "", "never-seen"])
def test_a_user_without_facts_gets_the_unchanged_prompt(history, user_id):
    facts = load_user_facts(user_id)

    assert facts == []
    for persona in PERSONAS.values():
        assert (
            Assistant(persona, facts=facts).instructions == persona.full_instructions()
        )


def test_a_missing_history_file_gives_the_unchanged_prompt(history, monkeypatch):
    _remember(history, "u-1", "Is a nurse")
    monkeypatch.delenv("CHAT_DB_PATH")

    facts = load_user_facts("u-1")

    assert facts == []
    assert Assistant(facts=facts).instructions == DEFAULT_PERSONA.full_instructions()


def test_an_unreadable_history_file_gives_the_unchanged_prompt(
    tmp_path, monkeypatch, caplog
):
    monkeypatch.setenv("CHAT_DB_PATH", str(tmp_path))  # a directory, not a database

    with caplog.at_level(logging.WARNING, logger="memory"):
        assert load_user_facts("u-1") == []
    assert len(caplog.records) == 1


class _FakeSession:
    def __init__(self):
        self.replies = []

    def generate_reply(self, *, instructions):
        self.replies.append(instructions)


OPENER = "Greet the user warmly and ask what they want to learn."


def test_a_fresh_session_speaks_the_personas_opener():
    session = _FakeSession()

    greet(session, None, replace(PERSONAS["tutor"], opener=OPENER))

    assert session.replies == [OPENER]


def test_a_persona_without_an_opener_stays_silent():
    session = _FakeSession()

    greet(session, None, DEFAULT_PERSONA)

    assert DEFAULT_PERSONA.opener is None
    assert session.replies == []


@pytest.mark.parametrize("mode", ["continue", "fork"])
def test_a_resumed_session_gets_the_welcome_and_not_the_opener(mode):
    session = _FakeSession()

    greet(session, ResumeRequest("c1", mode), replace(PERSONAS["tutor"], opener=OPENER))

    assert session.replies == [RESUME_WELCOME]


def test_a_resumed_session_with_no_opener_is_still_welcomed_back():
    session = _FakeSession()

    greet(session, ResumeRequest("c1", "continue"), DEFAULT_PERSONA)

    assert session.replies == [RESUME_WELCOME]
