"""Invariant: remove prior references and wording."""

from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_WORDS = ("de" + "precated", "leg" + "acy", "sh" + "im", "back" + "ward")
FORBIDDEN_IMPORT_MODULES = {
    "bijux_agent.pipeline.execution",
    "bijux_agent.pipeline.lifecycle",
    "bijux_agent.pipeline.interrupt",
    "bijux_agent.pipeline.io",
    "bijux_agent.pipeline.telemetry",
    "bijux_agent.pipeline.shard_processing",
    "bijux_agent.pipeline.controller",
    "bijux_agent.pipeline.controller_core",
    "bijux_agent.pipeline.controller_runtime",
    "bijux_agent.pipeline.results",
    "bijux_agent.pipeline.outcome",
    "bijux_agent.pipeline.failure",
    "bijux_agent.pipeline.completeness",
    "bijux_agent.pipeline.trace_validator",
    "bijux_agent.pipeline.trace_rules",
    "bijux_agent.pipeline.phases",
    "bijux_agent.pipeline.types",
    "bijux_agent.pipeline.decision",
    "bijux_agent.pipeline.stop_conditions",
    "bijux_agent.pipeline.convergence",
    "bijux_agent.filereaders",
    "bijux_agent.agents.filereader",
}
FORBIDDEN_IMPORT_PREFIXES = (
    "bijux_agent.filereaders.",
    "bijux_agent.agents.filereader.",
    "bijux_agent.pipeline.trace_rules.",
)
EXCLUDED_DIRS = {
    ".git",
    ".venv",
    ".mypy_cache",
    "artifacts",
    ".pytest_cache",
    ".benchmarks",
    ".ruff_cache",
    "__pycache__",
}


def _iter_repo_files(root: Path) -> list[Path]:
    return [
        path
        for path in root.rglob("*")
        if path.is_file() and not any(part in EXCLUDED_DIRS for part in path.parts)
    ]


def test_no_forbidden_words() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    violations: list[str] = []
    for path in _iter_repo_files(repo_root):
        try:
            content = path.read_text(encoding="utf-8", errors="ignore").lower()
        except OSError:
            continue
        if any(word in content for word in FORBIDDEN_WORDS):
            violations.append(str(path))
    assert not violations, f"Forbidden wording found in: {sorted(violations)}"


def _matches_forbidden(name: str) -> bool:
    if name in FORBIDDEN_IMPORT_MODULES:
        return True
    return name.startswith(FORBIDDEN_IMPORT_PREFIXES)


def test_no_deleted_import_paths() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    violations: list[str] = []
    for path in repo_root.rglob("*.py"):
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue
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
    assert not violations, "Deleted import paths detected:\n" + "\n".join(
        sorted(violations)
    )
