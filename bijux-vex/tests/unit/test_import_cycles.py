# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
import ast
from graphlib import TopologicalSorter, CycleError
from pathlib import Path

import pytest


def _core_import_graph() -> dict[str, set[str]]:
    root = Path(__file__).parents[2] / "src" / "bijux_vex" / "core"
    graph: dict[str, set[str]] = {}
    for path in root.rglob("*.py"):
        module = "bijux_vex.core." + ".".join(
            path.relative_to(root).with_suffix("").parts
        )
        tree = ast.parse(path.read_text())
        _attach_parents(tree)
        deps: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                if _guarded_by_type_checking(node):
                    continue
                for alias in node.names:
                    if (
                        alias.name.startswith("bijux_vex.core")
                        and alias.name not in _IGNORED
                    ):
                        deps.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if _guarded_by_type_checking(node):
                    continue
                if (
                    node.module
                    and node.module.startswith("bijux_vex.core")
                    and node.module not in _IGNORED
                ):
                    deps.add(node.module)
        graph[module] = deps
    return graph


def _guarded_by_type_checking(node: ast.AST) -> bool:
    parent = getattr(node, "parent", None)
    while parent:
        if isinstance(parent, ast.If) and isinstance(parent.test, ast.Name):
            if parent.test.id in {"TYPE_CHECKING", "_TYPE_CHECKING"}:
                return True
        parent = getattr(parent, "parent", None)
    return False


def _attach_parents(tree: ast.AST) -> None:
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            child.parent = parent


_IGNORED = {
    "bijux_vex.core.runtime.vector_execution",  # wrapper imports ExecutionRequest
    "bijux_vex.core.types",  # TYPE_CHECKING imports back into core
}


def test_core_imports_are_acyclic():
    graph = _core_import_graph()
    sorter = TopologicalSorter(graph)
    try:
        list(sorter.static_order())
    except CycleError as exc:  # pragma: no cover - assertion path
        pytest.fail(f"Circular import detected in core: {exc}")
