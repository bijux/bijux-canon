# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
"""
E2E coverage for the deterministic BM25 retrieval + grounded reasoning path.

SPDX-FileCopyrightText: © 2025 Bijan Mousavi
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import json
from pathlib import Path

from bijux_rar.boundaries.serde.trace_jsonl import read_trace_jsonl

from tests.e2e._helpers import read_json, run_cli, write_spec


def _corpus_fixture() -> Path:
    return Path(__file__).resolve().parents[2] / "fixtures" / "corpus_small.jsonl"


def test_local_bm25_run_produces_grounded_derived_claim(tmp_path: Path) -> None:
    artifacts_dir = tmp_path / "artifacts"
    spec_path = tmp_path / "spec.json"
    write_spec(
        spec_path,
        description="What is Rust?",
        constraints={
            "query": "Rust safety performance",
            "top_k": 2,
            "corpus_path": str(_corpus_fixture()),
            "needs_retrieval": True,
        },
    )

    cp = run_cli(
        [
            "run",
            "--spec",
            str(spec_path),
            "--seed",
            "0",
            "--artifacts-dir",
            str(artifacts_dir),
        ],
        check=True,
    )
    run_dir = Path(cp.stdout.strip())

    trace = read_trace_jsonl(run_dir / "trace.jsonl")
    claim_events = [ev for ev in trace.events if ev.kind == "claim_emitted"]
    assert len(claim_events) == 1
    claim = claim_events[0].claim

    assert claim.claim_type == "derived"
    assert claim.supports and claim.supports[0].kind == "evidence"
    cited_id = claim.supports[0].ref_id
    assert f"[evidence:{cited_id}:" in claim.statement
    assert claim.supports[0].span is not None
    assert claim.supports[0].snippet_sha256 is not None

    ev_events = [ev for ev in trace.events if ev.kind == "evidence_registered"]
    ids = {ev.evidence.id: ev.evidence for ev in ev_events}
    assert cited_id in ids
    ev_ref = ids[cited_id]
    ev_path = run_dir / ev_ref.content_path
    assert ev_path.exists()
    assert "Rust" in ev_path.read_text(encoding="utf-8")

    verify = read_json(run_dir / "verify.json")
    assert verify.get("failures") == []


def test_local_bm25_replay_has_same_fingerprint(tmp_path: Path) -> None:
    artifacts_dir = tmp_path / "artifacts"
    spec_path = tmp_path / "spec.json"
    write_spec(
        spec_path,
        description="What is Python?",
        constraints={
            "query": "Python scripting",
            "top_k": 2,
            "corpus_path": str(_corpus_fixture()),
            "needs_retrieval": True,
        },
    )
    cp = run_cli(
        [
            "run",
            "--spec",
            str(spec_path),
            "--seed",
            "0",
            "--artifacts-dir",
            str(artifacts_dir),
        ],
        check=True,
    )
    run_dir = Path(cp.stdout.strip())
    trace_path = run_dir / "trace.jsonl"

    rp = run_cli(["replay", "--trace", str(trace_path)], check=True)
    payload = json.loads(rp.stdout)
    assert (
        payload["original_trace_fingerprint"] == payload["replayed_trace_fingerprint"]
    )


def test_changing_corpus_changes_run_id(tmp_path: Path) -> None:
    artifacts_dir = tmp_path / "artifacts"
    corpus1 = tmp_path / "corpus1.jsonl"
    corpus2 = tmp_path / "corpus2.jsonl"
    corpus1.write_text(_corpus_fixture().read_text(encoding="utf-8"), encoding="utf-8")
    corpus2.write_text(
        _corpus_fixture().read_text(encoding="utf-8")
        + "\n"
        + '{"doc_id":"d4","text":"Extra doc."}',
        encoding="utf-8",
    )

    def _run(corpus: Path) -> Path:
        spec_path = tmp_path / f"spec_{corpus.name}.json"
        write_spec(
            spec_path,
            description="Q",
            constraints={
                "query": "Python",
                "top_k": 1,
                "corpus_path": str(corpus),
                "needs_retrieval": True,
            },
        )
        cp = run_cli(
            [
                "run",
                "--spec",
                str(spec_path),
                "--seed",
                "0",
                "--artifacts-dir",
                str(artifacts_dir),
            ],
            check=True,
        )
        return Path(cp.stdout.strip())

    run1 = _run(corpus1)
    run2 = _run(corpus2)
    assert run1.name != run2.name


def test_verifier_rejects_missing_citation_marker(tmp_path: Path) -> None:
    artifacts_dir = tmp_path / "artifacts"
    spec_path = tmp_path / "spec.json"
    write_spec(
        spec_path,
        description="What is Python?",
        constraints={
            "query": "Python",
            "top_k": 1,
            "corpus_path": str(_corpus_fixture()),
            "needs_retrieval": True,
            "min_supports_per_claim": 1,
        },
    )
    cp = run_cli(
        [
            "run",
            "--spec",
            str(spec_path),
            "--seed",
            "0",
            "--artifacts-dir",
            str(artifacts_dir),
        ],
        check=True,
    )
    run_dir = Path(cp.stdout.strip())

    trace_path = run_dir / "trace.jsonl"
    txt = trace_path.read_text(encoding="utf-8")
    txt = txt.replace("[evidence:", "[evi:")
    trace_path.write_text(txt, encoding="utf-8")

    vp = run_cli(
        [
            "verify",
            "--trace",
            str(trace_path),
            "--plan",
            str(run_dir / "plan.json"),
            "--fail-on-verify",
        ],
        check=False,
    )
    assert vp.returncode != 0

    out = run_dir / "verify.verify.json"
    report = read_json(out)
    msgs = "\n".join(f.get("message", "") for f in report.get("failures", []))
    assert "derived_claim_grounding" in msgs
