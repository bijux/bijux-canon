"""Invariant: agents remain passive (no orchestration/kernel control flow)."""

from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_IMPORT_PREFIXES = (
    "bijux_agent.pipeline",
    "bijux_agent.orchestrator",
)
FORBIDDEN_IMPORT_MODULES = {
    "bijux_agent.agents.kernel.execution_kernel",
    "bijux_agent.agents.kernel.lifecycle",
}
FORBIDDEN_SELF_CALLS = {"run", "revise", "fail"}


def _iter_agent_files(root: Path) -> list[Path]:
    agents_root = root / "src" / "bijux_agent" / "agents"
    excluded = {"base.py", "execution_kernel.py", "lifecycle.py"}
    return [
        path
        for path in agents_root.rglob("*.py")
        if path.is_file() and path.name not in excluded
    ]


def _matches_forbidden_import(module: str | None) -> bool:
    if module is None:
        return False
    if module in FORBIDDEN_IMPORT_MODULES:
        return True
    return module.startswith(FORBIDDEN_IMPORT_PREFIXES)


def test_agents_are_passive() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    violations: list[str] = []
    for path in _iter_agent_files(repo_root):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                violations.extend(
                    [
                        f"{path}:{node.lineno} import {alias.name}"
                        for alias in node.names
                        if _matches_forbidden_import(alias.name)
                    ]
                )
            elif isinstance(node, ast.ImportFrom):
                if _matches_forbidden_import(node.module):
                    violations.append(f"{path}:{node.lineno} from {node.module}")
            elif isinstance(node, ast.Call):
                func = node.func
                if (
                    isinstance(func, ast.Attribute)
                    and func.attr in FORBIDDEN_SELF_CALLS
                    and isinstance(func.value, ast.Name)
                    and func.value.id == "self"
                ):
                    violations.append(f"{path}:{node.lineno} self.{func.attr}()")

    assert not violations, "Passive agent violations found:\n" + "\n".join(violations)
