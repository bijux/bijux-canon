# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
import pathlib
from typing import Iterable

import yaml
# pyright: reportMissingModuleSource=false


def _flatten_nav(nav: Iterable[dict | str]) -> set[pathlib.Path]:
    """Collect all nav entries as paths relative to docs/."""
    paths: set[pathlib.Path] = set()
    for entry in nav:
        if isinstance(entry, str):
            paths.add(pathlib.Path(entry))
            continue
        if isinstance(entry, dict):
            for value in entry.values():
                if isinstance(value, str):
                    paths.add(pathlib.Path(value))
                elif isinstance(value, list):
                    paths |= _flatten_nav(value)
                elif value is None:
                    # MkDocs allows separators; ignore them
                    continue
                else:
                    raise TypeError(f"Unsupported nav entry: {value!r}")
        else:
            raise TypeError(f"Unsupported nav entry: {entry!r}")
    return paths


def test_all_docs_are_reachable_from_nav():
    repo_root = pathlib.Path(__file__).resolve().parents[2]
    mkdocs_yaml = repo_root / "mkdocs.yml"
    docs_root = repo_root / "docs"
    data = yaml.safe_load(mkdocs_yaml.read_text())
    nav_entries = _flatten_nav(data["nav"])
    nav_docs = {p for p in nav_entries if p.suffix == ".md"}

    doc_files = {
        path.relative_to(docs_root)
        for path in docs_root.rglob("*.md")
        if "site" not in path.parts
    }

    # Allow root README.md inclusion via include-markdown (not under docs/)
    missing_in_nav = doc_files - nav_docs
    assert not missing_in_nav, (
        f"Documentation files missing from mkdocs nav: {sorted(missing_in_nav)}"
    )


def test_readme_points_to_start_here():
    repo_root = pathlib.Path(__file__).resolve().parents[2]
    readme = (repo_root / "README.md").read_text()
    assert "docs/user/start_here.md" in readme, "README must link to start_here"


def test_start_here_exists_and_is_linked():
    repo_root = pathlib.Path(__file__).resolve().parents[2]
    start_here = repo_root / "docs/user/start_here.md"
    assert start_here.exists(), "docs/user/start_here.md must exist"
    index = (repo_root / "docs/index.md").read_text()
    if "user/start_here.md" not in index:
        readme = (repo_root / "README.md").read_text()
        assert "docs/user/start_here.md" in readme, "README must link to start_here"


def test_no_bijux_rar_mentions_in_docs():
    repo_root = pathlib.Path(__file__).resolve().parents[2]
    docs_root = repo_root / "docs"
    offending = []
    for path in docs_root.rglob("*.md"):
        if "bijux-rar" in path.read_text():
            offending.append(path)
    assert not offending, (
        f"Docs must be self-contained; found bijux-rar mentions in {offending}"
    )


def test_schema_is_referenced_from_api_docs():
    repo_root = pathlib.Path(__file__).resolve().parents[2]
    api_docs = (repo_root / "docs/api/index.md").read_text()
    assert "api/v1/schema.yaml" in api_docs, "API docs must reference canonical schema"
