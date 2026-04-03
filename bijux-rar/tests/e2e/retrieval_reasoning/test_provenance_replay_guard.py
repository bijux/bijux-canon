# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest

from tests.e2e._helpers import run_cli, write_spec


def _run_and_get_dir(tmp_path: Path) -> Path:
    artifacts = tmp_path / "artifacts"
    spec_path = tmp_path / "spec.json"
    write_spec(
        spec_path,
        description="provenance replay guard",
        constraints={"needs_retrieval": True, "top_k": 1},
    )
    cp = run_cli(
        [
            sys.executable,
            "-m",
            "bijux_rar",
            "run",
            "--spec",
            str(spec_path),
            "--seed",
            "0",
            "--preset",
            "rar",
            "--artifacts-dir",
            str(artifacts),
        ]
    )
    return Path(cp.stdout.strip())


def test_replay_refuses_when_corpus_tampered(tmp_path: Path) -> None:
    run_dir = _run_and_get_dir(tmp_path)
    corpus = run_dir / "provenance" / "corpus.jsonl"
    assert corpus.exists()
    corpus.write_text(corpus.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    cmd = [
        sys.executable,
        "-m",
        "bijux_rar",
        "replay",
        "--trace",
        str(run_dir / "trace.jsonl"),
    ]
    with pytest.raises(subprocess.CalledProcessError):
        run_cli(cmd, check=True)


def test_replay_succeeds_with_intact_provenance(tmp_path: Path) -> None:
    run_dir = _run_and_get_dir(tmp_path)
    cmd = [
        sys.executable,
        "-m",
        "bijux_rar",
        "replay",
        "--trace",
        str(run_dir / "trace.jsonl"),
    ]
    res = run_cli(cmd, check=True)
    assert res.returncode == 0
