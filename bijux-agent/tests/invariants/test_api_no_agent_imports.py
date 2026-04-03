"""Invariant: API layer cannot import agent internals."""

from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_PREFIXES = ("bijux_agent.agents",)
FORBIDDEN_MODULES = {
    "bijux_agent.agents.kernel.execution_kernel",
}
FORBIDDEN_NAMES = {"AgentExecutionKernel"}


def _matches_forbidden(module: str) -> bool:
    return module in FORBIDDEN_MODULES or module.startswith(FORBIDDEN_PREFIXES)


def test_api_has_no_agent_imports() -> None:
    api_root = Path(__file__).resolve().parents[2] / "src" / "bijux_agent" / "api"
    violations: list[str] = []
    for path in api_root.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                violations.extend(
                    [
                        f"{path}:{node.lineno} import {alias.name}"
                        for alias in node.names
                        if _matches_forbidden(alias.name)
                    ]
                )
            elif isinstance(node, ast.ImportFrom):
                if node.module and _matches_forbidden(node.module):
                    violations.append(f"{path}:{node.lineno} from {node.module}")
                violations.extend(
                    [
                        f"{path}:{node.lineno} import {alias.name}"
                        for alias in node.names
                        if alias.name in FORBIDDEN_NAMES
                    ]
                )
    assert not violations, "API layer imports agents:\n" + "\n".join(violations)
