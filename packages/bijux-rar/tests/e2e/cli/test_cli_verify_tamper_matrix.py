# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest


def _run_with_evidence(tmp_path: Path, write_spec, run_cli, *, seed: int) -> Path:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    spec_path = write_spec(
        description=f"tamper seed={seed}",
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
            str(seed),
            "--preset",
            "rar",
            "--artifacts-dir",
            str(artifacts),
        ]
    )
    return Path(p.stdout.strip())


@pytest.mark.e2e
@pytest.mark.parametrize(
    "seed,mutation",
    [
        (0, "flip_byte"),
        (1, "truncate"),
        (2, "append"),
        (3, "delete"),
        (4, "overwrite"),
        (5, "flip_byte"),
        (6, "truncate"),
        (7, "append"),
        (8, "delete"),
        (9, "overwrite"),
    ],
)
def test_cli_verify_fails_on_evidence_tampering(
    tmp_path: Path, write_spec, run_cli, seed: int, mutation: str
) -> None:
    run_dir = _run_with_evidence(tmp_path, write_spec, run_cli, seed=seed)
    ev_files = sorted((run_dir / "evidence").glob("*.txt"))
    assert ev_files

    target = ev_files[0]
    b = target.read_bytes()
    if mutation == "flip_byte":
        target.write_bytes(bytes([(b[0] ^ 0xFF)]) + b[1:])
    elif mutation == "truncate":
        target.write_bytes(b[: max(0, len(b) // 2)])
    elif mutation == "append":
        target.write_bytes(b + b"\nTAMPER")
    elif mutation == "delete":
        target.unlink()
    elif mutation == "overwrite":
        target.write_bytes(b"totally different")
    else:
        raise AssertionError("unknown mutation")

    cmd = [
        sys.executable,
        "-m",
        "bijux_rar",
        "verify",
        "--trace",
        str(run_dir / "trace.jsonl"),
        "--plan",
        str(run_dir / "plan.json"),
        "--fail-on-verify",
    ]
    with pytest.raises(subprocess.CalledProcessError):
        run_cli(cmd)


@pytest.mark.e2e
def test_cli_verify_fails_on_support_snippet_tamper(
    tmp_path: Path, write_spec, run_cli
) -> None:
    run_dir = _run_with_evidence(tmp_path, write_spec, run_cli, seed=123)
    trace_path = run_dir / "trace.jsonl"
    lines = trace_path.read_text(encoding="utf-8").splitlines()
    mutated: list[str] = []
    for line in lines:
        obj = json.loads(line)
        event = obj.get("event") if "event" in obj else obj
        if event.get("kind") == "claim_emitted":
            claim = event.get("claim", {})
            supports = claim.get("supports") or []
            if supports:
                supports[0]["snippet_sha256"] = "0" * 64
                if "event" in obj:
                    obj["event"]["claim"]["supports"] = supports
                else:
                    obj["claim"]["supports"] = supports
        mutated.append(json.dumps(obj, sort_keys=True, ensure_ascii=False))
    trace_path.write_text(
        "\n".join(mutated) + ("\n" if mutated else ""), encoding="utf-8"
    )

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
