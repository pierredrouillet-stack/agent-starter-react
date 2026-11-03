"""The profile the user wrote about themselves, in a plain file beside the agent."""

import logging
from pathlib import Path

logger = logging.getLogger("user_profile")

# Resolved from this file, not the current directory, so where the worker starts does not matter.
PROFILE_PATH = Path(__file__).resolve().parent.parent / "profile.md"

# Characters kept in the prompt on every call; a longer file is refused whole, never cut.
MAX_PROFILE_LENGTH = 4000


def load_user_profile() -> str:
    """The profile text to give a session at its start; any problem means none.

    A missing file is the normal case and silent. An unreadable, empty or
    oversized file is logged and ignored.
    """
    try:
        text = PROFILE_PATH.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return ""
    except (OSError, ValueError) as exc:
        logger.warning("could not read the user's profile: %s", exc)
        return ""
    if not text:
        logger.warning("ignoring the user's profile: %s is empty", PROFILE_PATH.name)
        return ""
    if len(text) > MAX_PROFILE_LENGTH:
        logger.warning(
            "ignoring the user's profile: %s is %d characters, over the %d allowed",
            PROFILE_PATH.name,
            len(text),
            MAX_PROFILE_LENGTH,
        )
        return ""
    return text
