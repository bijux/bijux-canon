"""Invariant: agents must not import pipeline/orchestrator modules."""

from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_PREFIXES = ("bijux_agent.pipeline", "bijux_agent.orchestrator")
FORBIDDEN_RELATIVE = ("pipeline", "orchestrator")


def _iter_agent_files(root: Path) -> list[Path]:
    agents_root = root / "src" / "bijux_agent" / "agents"
    return [path for path in agents_root.rglob("*.py") if path.is_file()]


def _matches_forbidden(module: str, level: int) -> bool:
    return module.startswith(FORBIDDEN_PREFIXES) or (
        level > 0
        and (
            module in FORBIDDEN_RELATIVE
            or module.startswith(f"{FORBIDDEN_RELATIVE[0]}.")
            or module.startswith(f"{FORBIDDEN_RELATIVE[1]}.")
        )
    )


def test_agents_no_orchestration_imports() -> None:
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
                        if alias.name.startswith(FORBIDDEN_PREFIXES)
                    ]
                )
            elif isinstance(node, ast.ImportFrom):
                if node.module and _matches_forbidden(node.module, node.level):
                    violations.append(f"{path}:{node.lineno} from {node.module} import")
                elif node.module == "bijux_agent":
                    violations.extend(
                        [
                            f"{path}:{node.lineno} from bijux_agent import {alias.name}"
                            for alias in node.names
                            if alias.name in FORBIDDEN_RELATIVE
                        ]
                    )
                elif node.module is None and node.level > 0:
                    violations.extend(
                        [
                            f"{path}:{node.lineno} from . import {alias.name}"
                            for alias in node.names
                            if alias.name in FORBIDDEN_RELATIVE
                        ]
                    )
    assert not violations, "Forbidden imports found:\n" + "\n".join(violations)
