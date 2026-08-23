"""Invariant: Agent application services do not import product siblings."""

from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_PREFIXES = (
    "bijux_canon_index",
    "bijux_canon_ingest",
    "bijux_canon_reason",
    "bijux_canon_runtime",
)


def test_application_services_keep_runtime_neutral_ports() -> None:
    package_root = Path(__file__).resolve().parents[2]
    application_root = package_root / "src" / "bijux_canon_agent" / "application"
    violations: list[str] = []
    for path in application_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                violations.extend(
                    f"{path}:{node.lineno} import {alias.name}"
                    for alias in node.names
                    if alias.name.startswith(FORBIDDEN_PREFIXES)
                )
            elif (
                isinstance(node, ast.ImportFrom)
                and node.module is not None
                and node.module.startswith(FORBIDDEN_PREFIXES)
            ):
                violations.append(f"{path}:{node.lineno} from {node.module} import")

    assert not violations, "Agent application imported a product sibling:\n" + "\n".join(
        violations
    )
