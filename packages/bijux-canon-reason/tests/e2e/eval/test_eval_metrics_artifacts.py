# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

import json
from pathlib import Path

from bijux_canon_reason.interfaces.cli.main import app
from typer.testing import CliRunner

runner = CliRunner()


def test_eval_outputs_metrics_files(tmp_path: Path) -> None:
    res = runner.invoke(
        app,
        [
            "eval",
            "--suite",
            "small",
            "--artifacts-dir",
            str(tmp_path),
        ],
    )
    assert res.exit_code == 0
    summary = tmp_path / "eval" / "small" / "summary.json"
    cases = tmp_path / "eval" / "small" / "cases.jsonl"
    assert summary.exists()
    assert cases.exists()

    payload = json.loads(summary.read_text(encoding="utf-8"))
    metrics = payload.get("metrics", {})
    assert 0.0 <= metrics.get("recall_at_k", 0) <= 1.0
    assert 0.0 <= metrics.get("alignment_rate", 0) <= 1.0
    assert 0.0 <= metrics.get("insufficiency_rate", 0) <= 1.0
    assert 0.0 <= metrics.get("faithfulness", 0) >= 0.0

    rows = [json.loads(line) for line in cases.read_text(encoding="utf-8").splitlines()]
    assert rows, "cases.jsonl should have per-case rows"
    for row in rows:
        assert "recall_at_k" in row
        assert "alignment_rate" in row
        assert "faithfulness" in row
        assert "verification_checks_failed" in row
        assert "claims_failed" in row
