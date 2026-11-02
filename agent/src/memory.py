"""Facts the agent remembers about a user across calls.

See docs/conversation-storage.md for the table this module reads and writes.
"""

import json
import logging

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
