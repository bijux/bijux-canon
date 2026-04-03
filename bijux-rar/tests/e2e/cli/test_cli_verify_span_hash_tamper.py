# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

# SPDX-FileCopyrightText: © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT

from pathlib import Path
import json
import subprocess
import sys

import pytest


def _run_with_evidence(tmp_path: Path, write_spec, run_cli) -> Path:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    spec_path = write_spec(
        description="span-hash tamper",
        constraints={"needs_retrieval": True, "top_k": 2},
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
            "0",
            "--preset",
            "rar",
            "--artifacts-dir",
            str(artifacts),
        ]
    )
    return Path(p.stdout.strip())


@pytest.mark.e2e
def test_verify_fails_when_snippet_hash_tampered(
    tmp_path: Path, write_spec, run_cli
) -> None:
    run_dir = _run_with_evidence(tmp_path, write_spec, run_cli)
    trace_path = run_dir / "trace.jsonl"
    lines = trace_path.read_text(encoding="utf-8").splitlines()

    mutated: list[str] = []
    mutated_any = False
    for line in lines:
        obj = json.loads(line)
        ev = obj.get("event") if "event" in obj else obj
        if ev.get("kind") == "claim_emitted":
            claim = ev.get("claim", {})
            supports = claim.get("supports") or []
            if supports:
                old_sha = supports[0].get("snippet_sha256")
                if isinstance(old_sha, str) and len(old_sha) == 64:
                    new_sha = ("0" if old_sha[-1] != "0" else "1") + old_sha[1:]
                    supports[0]["snippet_sha256"] = new_sha
                    b0, b1 = supports[0].get("span", [0, 0])
                    eid = supports[0].get("ref_id")
                    marker_old = f"[evidence:{eid}:{b0}-{b1}:{old_sha}]"
                    marker_new = f"[evidence:{eid}:{b0}-{b1}:{new_sha}]"
                    claim["statement"] = str(claim.get("statement", "")).replace(
                        marker_old, marker_new
                    )
                    mutated_any = True
        mutated.append(json.dumps(obj, ensure_ascii=False))

    assert mutated_any, "did not find claim to tamper"
    trace_path.write_text("\n".join(mutated) + "\n", encoding="utf-8")

    cmd = [
        sys.executable,
        "-m",
        "bijux_rar",
        "verify",
        "--trace",
        str(trace_path),
        "--plan",
        str(run_dir / "plan.json"),
        "--fail-on-verify",
    ]
    with pytest.raises(subprocess.CalledProcessError):
        run_cli(cmd)
