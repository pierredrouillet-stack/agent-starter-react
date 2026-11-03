import logging

import pytest

import user_profile
from user_profile import MAX_PROFILE_LENGTH, load_user_profile


@pytest.fixture
def profile_file(tmp_path, monkeypatch):
    path = tmp_path / "profile.md"
    monkeypatch.setattr(user_profile, "PROFILE_PATH", path)
    return path


def test_the_profile_is_the_stripped_file_text(profile_file):
    profile_file.write_text(
        "\n  I am Sam, a nurse.\nCall me Sam.\n\n", encoding="utf-8"
    )

    assert load_user_profile() == "I am Sam, a nurse.\nCall me Sam."


def test_the_default_path_is_profile_md_in_the_agent_folder():
    assert user_profile.PROFILE_PATH.name == "profile.md"
    assert user_profile.PROFILE_PATH.parent.name == "agent"


def test_a_missing_file_is_silently_empty(profile_file, caplog):
    with caplog.at_level(logging.WARNING, logger="user_profile"):
        assert load_user_profile() == ""
    assert caplog.records == []


@pytest.mark.parametrize("content", ["", "  \n\t\n"])
def test_a_blank_file_is_empty_with_a_warning(profile_file, content, caplog):
    profile_file.write_text(content, encoding="utf-8")

    with caplog.at_level(logging.WARNING, logger="user_profile"):
        assert load_user_profile() == ""
    assert "empty" in caplog.text


def test_an_unreadable_file_is_empty_with_a_warning(profile_file, caplog):
    profile_file.mkdir()  # a directory cannot be read as a file

    with caplog.at_level(logging.WARNING, logger="user_profile"):
        assert load_user_profile() == ""
    assert "could not read" in caplog.text


def test_a_file_that_is_not_text_is_empty_with_a_warning(profile_file, caplog):
    profile_file.write_bytes(b"\xff\xfe\x00bad")

    with caplog.at_level(logging.WARNING, logger="user_profile"):
        assert load_user_profile() == ""
    assert "could not read" in caplog.text


def test_a_file_at_the_cap_is_kept(profile_file):
    profile_file.write_text("x" * MAX_PROFILE_LENGTH, encoding="utf-8")

    assert load_user_profile() == "x" * MAX_PROFILE_LENGTH


def test_an_oversized_file_is_refused_whole_with_a_warning(profile_file, caplog):
    profile_file.write_text("x" * (MAX_PROFILE_LENGTH + 1), encoding="utf-8")

    with caplog.at_level(logging.WARNING, logger="user_profile"):
        assert load_user_profile() == ""
    assert "over the 4000 allowed" in caplog.text


def test_an_edit_is_seen_by_the_next_read(profile_file):
    profile_file.write_text("I am Sam.", encoding="utf-8")
    assert load_user_profile() == "I am Sam."

    profile_file.write_text("I am Alex.", encoding="utf-8")
    assert load_user_profile() == "I am Alex."

    profile_file.unlink()
    assert load_user_profile() == ""
