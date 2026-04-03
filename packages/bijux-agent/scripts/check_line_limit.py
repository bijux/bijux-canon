#!/usr/bin/env python3
"""Ensure no Python modules exceed the configured line limit."""

from __future__ import annotations

from pathlib import Path
import sys

MAX_LINES = 600
EXCLUDED_DIRS = {"artifacts", ".venv", "htmlcov", "build", "dist", "node_modules", ".tox"}
EXEMPT_PATHS = {
    "src/bijux_agent/agents/critique/core.py",
    "src/bijux_agent/agents/file_reader/agent.py",
    "src/bijux_agent/agents/summarizer/core.py",
    "src/bijux_agent/agents/validator/agent.py",
    "src/bijux_agent/agents/file_reader/capabilities/universal_file_reader_core.py",
    "src/bijux_agent/pipeline/pipeline.py",
    "tests/unit/test_pipeline_flow.py",
}


def _is_excluded(path: Path) -> bool:
    return any(part in EXCLUDED_DIRS for part in path.parts)


def main() -> int:
    root = Path(".").resolve()
    offenders: list[tuple[Path, int]] = []
    for path in root.rglob("*.py"):
        if _is_excluded(path) or path.name.startswith("."):
            continue
        relative = str(path.relative_to(root))
        if relative in EXEMPT_PATHS:
            continue
        try:
            line_count = sum(1 for _ in path.open("r", encoding="utf-8", errors="ignore"))
        except FileNotFoundError:
            continue
        if line_count > MAX_LINES:
            offenders.append((path, line_count))

    if offenders:
        print(
            "error: the following Python files exceed the "
            f"{MAX_LINES}-line limit:"
        )
        for path, count in sorted(offenders):
            print(f" - {path.relative_to(root)} ({count} lines)")
        return 1

    print("line limit check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
