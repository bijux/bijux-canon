# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from pathlib import Path

from bijux_canon_index.core.errors import ValidationError
from bijux_canon_index.interfaces.cli.workspace_setup import initialize_workspace
import pytest


def test_initialize_workspace_creates_config_artifacts_and_gitignore(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "bijux_canon_index.toml"
    gitignore_path = tmp_path / ".gitignore"
    gitignore_path.write_text("node_modules/\n", encoding="utf-8")

    cwd = Path.cwd()
    try:
        import os

        os.chdir(tmp_path)
        result = initialize_workspace(config_path, force=False)
    finally:
        os.chdir(cwd)

    assert result == {"status": "initialized", "config": str(config_path)}
    assert config_path.exists()
    assert (tmp_path / "artifacts" / "bijux-canon-index" / "runs").is_dir()
    assert gitignore_path.read_text(encoding="utf-8").splitlines() == [
        "node_modules/",
        "artifacts/",
        "*.sqlite",
        "*.faiss",
        "*.meta.json",
    ]


def test_initialize_workspace_requires_force_for_existing_config(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "bijux_canon_index.toml"
    config_path.write_text("existing = true\n", encoding="utf-8")

    with pytest.raises(ValidationError):
        initialize_workspace(config_path, force=False)
