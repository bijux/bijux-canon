"""Invariant: HTTP adapter stays isolated from core internals."""

from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_PREFIXES = (
    "bijux_agent.agents",
    "bijux_agent.pipeline.convergence",
    "bijux_agent.agents.kernel",
)
FORBIDDEN_MODULES = {
    "bijux_agent.agents.kernel.execution_kernel",
}


def _matches_forbidden(module: str) -> bool:
    return module in FORBIDDEN_MODULES or module.startswith(FORBIDDEN_PREFIXES)


def test_httpapi_isolated_from_agents() -> None:
    http_root = Path(__file__).resolve().parents[2] / "src" / "bijux_agent" / "httpapi"
    violations: list[str] = []
    for path in http_root.rglob("*.py"):
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
            elif (
                isinstance(node, ast.ImportFrom)
                and node.module
                and _matches_forbidden(node.module)
            ):
                violations.append(f"{path}:{node.lineno} from {node.module}")
    assert not violations, "HTTP API imports core internals:\n" + "\n".join(violations)
