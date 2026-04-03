# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import tomllib
from pathlib import Path


def test_packaging_metadata_hardened() -> None:
    root = Path(__file__).resolve().parents[2]
    with open(root / "pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    project = data["project"]
    classifiers = set(project.get("classifiers", []))
    assert "Programming Language :: Python :: 3 :: Only" in classifiers
    assert "Intended Audience :: Developers" in classifiers
    assert project.get("requires-python") and project["requires-python"].startswith(
        ">="
    )

    urls = project.get("urls", {})
    for key in ("Documentation", "Repository", "Homepage"):
        assert key in urls and urls[key], f"missing URL for {key}"
    assert urls.get("Documentation", "").startswith("https://bijux.github.io/")
    assert urls.get("Repository", "").startswith("https://github.com/")

    # Minimal dependency surface: core deps are limited.
    deps = project.get("dependencies", [])
    assert len(deps) <= 4, "core dependency surface should stay minimal"
