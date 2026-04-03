from __future__ import annotations

from bijux_agent.config import validate_keys as core_validate
from bijux_agent.config.env import validate_keys as env_validate


def test_validate_keys_is_deduplicated() -> None:
    """Guard against multiple validate_keys definitions reappearing."""
    assert core_validate is env_validate
