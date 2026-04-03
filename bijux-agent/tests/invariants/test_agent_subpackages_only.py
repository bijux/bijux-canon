"""Invariant: agent logic lives in subpackages, not flat modules."""

from __future__ import annotations

from pathlib import Path

ALLOWED_TOP_LEVEL = {
    "__init__.py",
    "base.py",
}


def test_agents_live_in_subpackages() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    agents_root = repo_root / "src" / "bijux_agent" / "agents"
    top_level = {path.name for path in agents_root.glob("*.py") if path.is_file()}
    unexpected = sorted(top_level - ALLOWED_TOP_LEVEL)
    assert not unexpected, (
        "Agent modules must live in subpackages (agents/*/agent.py). "
        f"Unexpected top-level modules: {unexpected}"
    )
