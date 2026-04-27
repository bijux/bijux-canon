from __future__ import annotations

import importlib

from bijux_canon_agent.config import validate_keys as core_validate
from bijux_canon_agent.config.env import load_environment
from bijux_canon_agent.config.env import validate_keys as env_validate
import pytest


def test_validate_keys_is_deduplicated() -> None:
    """Guard against multiple validate_keys definitions reappearing."""
    assert core_validate is env_validate


def test_load_environment_skips_missing_dotenv(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """Missing python-dotenv should not block plain environment-driven installs."""
    env_path = tmp_path / ".env"
    env_path.write_text("OPENAI_API_KEY=test-key\n", encoding="utf-8")

    def _raise(name: str):
        if name == "dotenv":
            raise ModuleNotFoundError(name)
        return importlib.import_module(name)

    monkeypatch.setattr("bijux_canon_agent.config.env.importlib.import_module", _raise)

    load_environment(env_path)
