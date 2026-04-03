# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from pathlib import Path
import hashlib
import json
import sys

import pytest


def _sha256_path(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.mark.e2e
@pytest.mark.parametrize(
    "seed,top_k",
    [(0, 1), (1, 1), (2, 2), (3, 2), (4, 3), (5, 3), (6, 4), (7, 4), (8, 5), (9, 5)],
)
def test_cli_run_writes_evidence_files_and_manifest(
    tmp_path: Path, write_spec, run_cli, seed: int, top_k: int
) -> None:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)

    spec_path = write_spec(
        description=f"evidence contract seed={seed} top_k={top_k}",
        constraints={"needs_retrieval": True, "top_k": top_k},
    )

    p = run_cli(
        [
            sys.executable,
            "-m",
            "bijux_rar",
            "run",
            "--spec",
            str(spec_path),
            "--seed",
            str(seed),
            "--preset",
            "rar",
            "--artifacts-dir",
            str(artifacts),
        ]
    )
    run_dir = Path(p.stdout.strip())

    evidence_dir = run_dir / "evidence"
    assert evidence_dir.exists()

    files = sorted(evidence_dir.glob("*.txt"))
    assert 1 <= len(files) <= top_k

    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert isinstance(manifest, dict)
    evidence_manifest = {k: v for k, v in manifest.items() if k.startswith("evidence/")}
    assert 1 <= len(evidence_manifest) <= top_k

    for rel, expected_sha in manifest.items():
        abs_path = run_dir / rel
        assert abs_path.exists(), f"manifest points to missing file: {rel}"
        assert _sha256_path(abs_path) == expected_sha

    verify = json.loads((run_dir / "verify.json").read_text(encoding="utf-8"))
    checks = {c["name"]: c for c in verify["checks"]}
    assert checks["evidence_hashes"]["passed"] is True
