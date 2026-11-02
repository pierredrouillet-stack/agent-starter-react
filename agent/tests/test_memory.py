import logging

import pytest

from memory import parse_user


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
