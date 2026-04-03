"""Invariant: agents must not override run/revise/fail hooks."""

from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_METHODS = {"run", "revise", "fail"}


def _iter_agent_files(root: Path) -> list[Path]:
    agents_root = root / "src" / "bijux_agent" / "agents"
    excluded = {"base.py", "execution_kernel.py"}
    return [
        path
        for path in agents_root.rglob("*.py")
        if path.is_file() and path.name not in excluded
    ]


def test_agents_do_not_override_lifecycle_hooks() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    violations: list[str] = []
    for path in _iter_agent_files(repo_root):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if (
                        isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and item.name in FORBIDDEN_METHODS
                    ):
                        violations.extend(
                            [f"{path}:{item.lineno} {node.name}.{item.name}"]
                        )
    assert not violations, "Lifecycle overrides found:\n" + "\n".join(violations)
