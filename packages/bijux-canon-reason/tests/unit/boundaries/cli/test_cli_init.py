# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from bijux_rar.boundaries.cli import init as init_cmd

runner = CliRunner()


def test_init_creates_sample_spec(tmp_path: Path) -> None:
    res = runner.invoke(init_cmd.app, ["--target", str(tmp_path)])
    assert res.exit_code == 0
    sample = tmp_path / "sample_spec.json"
    assert sample.exists()
    text = sample.read_text(encoding="utf-8")
    assert "capital of France" in text
