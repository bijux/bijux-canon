# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from pathlib import Path


def _parse_graph(doc_path: Path) -> dict[str, list[str]]:
    graph: dict[str, list[str]] = {}
    for line in doc_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("- "):
            continue
        if "->" not in line:
            continue
        lhs, rhs = line[2:].split("->", 1)
        doc = lhs.strip()
        deps_raw = rhs.strip()
        if deps_raw in {"[]", ""}:
            deps: list[str] = []
        else:
            deps = [d.strip() for d in deps_raw.split(",") if d.strip()]
        graph[doc] = deps
    return graph


def test_doc_dependency_graph_is_acyclic_and_complete() -> None:
    root = Path(__file__).resolve().parents[2]
    doc_path = root / "docs" / "spec" / "doc_dependency.md"
    assert doc_path.exists(), "docs/spec/doc_dependency.md missing"
    graph = _parse_graph(doc_path)
    # All referenced docs must exist
    for doc, deps in graph.items():
        # docs listed in the graph are relative to docs/spec or docs/maintainer/user
        spec_path = root / "docs" / "spec" / doc
        maint_path = root / "docs" / "maintainer" / doc
        user_path = root / "docs" / "user" / doc
        assert (
            spec_path.exists() or maint_path.exists() or user_path.exists()
        ), f"doc listed but missing: {doc}"
        for dep in deps:
            dep_spec = root / "docs" / "spec" / dep
            dep_maint = root / "docs" / "maintainer" / dep
            dep_user = root / "docs" / "user" / dep
            assert (
                dep_spec.exists() or dep_maint.exists() or dep_user.exists()
            ), f"dependency missing: {dep}"

    # Detect cycles via DFS
    temp_mark: set[str] = set()
    perm_mark: set[str] = set()

    def visit(node: str) -> None:
        if node in perm_mark:
            return
        if node in temp_mark:
            raise AssertionError(f"cycle detected in doc dependency graph at {node}")
        temp_mark.add(node)
        for dep in graph.get(node, []):
            visit(dep)
        temp_mark.remove(node)
        perm_mark.add(node)

    for node in graph:
        visit(node)

    # Ensure topological sorting is possible
    assert len(perm_mark) == len(graph), "not all docs were processed (disconnected?)"
