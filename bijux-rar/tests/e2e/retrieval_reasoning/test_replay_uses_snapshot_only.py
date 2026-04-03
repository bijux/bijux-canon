# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
"""Replay must succeed using pinned corpus snapshot even if original corpus is gone."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

from tests.e2e._helpers import run_cli, write_spec


@pytest.mark.e2e
def test_replay_works_after_corpus_deleted(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)

    # create a temporary corpus
    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text('{"doc_id":"d1","text":"deterministic corpus text"}\n', encoding="utf-8")

    spec_path = tmp_path / "spec.json"
    write_spec(
        spec_path,
        description="replay without corpus present",
        constraints={"needs_retrieval": True, "top_k": 1, "corpus_path": str(corpus)},
    )

    # Run
    p = run_cli(
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
        ],
        check=True,
    )
    run_dir = Path(p.stdout.strip())

    # Delete the original corpus path
    corpus.unlink()

    # Replay should still succeed using pinned provenance
    rp = run_cli(
        [
            sys.executable,
            "-m",
            "bijux_rar",
            "replay",
            "--trace",
            str(run_dir / "trace.jsonl"),
        ],
        check=True,
    )
    assert rp.returncode == 0
