# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

import hashlib
from pathlib import Path

from bijux_rar.core.rar_types import ProblemSpec, TraceEventKind
from bijux_rar.rar.execution.executor import ExecutionPolicy, execute_plan
from bijux_rar.rar.execution.runtime import Runtime
from bijux_rar.rar.planning.planner import plan_problem


def test_executor_emits_claims_with_grounded_supports(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text(
        '{"doc_id":"d1","text":"Rust is fast and memory safe."}',
        encoding="utf-8",
    )
    spec = ProblemSpec(
        description="What is Rust?",
        constraints={
            "query": "Rust",
            "top_k": 1,
            "corpus_path": str(corpus),
            "needs_retrieval": True,
            "min_supports_per_claim": 1,
        },
    )
    plan = plan_problem(spec=spec, preset="rar")
    runtime = Runtime.local_bm25(
        seed=0, corpus_path=corpus, artifacts_dir=tmp_path
    )

    result = execute_plan(
        spec=spec,
        plan=plan,
        runtime=runtime,
        policy=ExecutionPolicy(fail_fast=True),
    )

    claim_events = [
        ev for ev in result.trace.events if ev.kind == TraceEventKind.claim_emitted
    ]
    assert claim_events, "no claims emitted"
    claim = claim_events[0].claim
    assert claim.supports
    sup = claim.supports[0]
    assert sup.span is not None and sup.snippet_sha256 is not None

    # Verify snippet hash matches persisted evidence bytes
    ev_event = next(
        ev
        for ev in result.trace.events
        if ev.kind == TraceEventKind.evidence_registered
    )
    ev_path = (tmp_path / ev_event.evidence.content_path).resolve()
    data = ev_path.read_bytes()
    b0, b1 = sup.span
    assert data[b0:b1]
    expected_sha = hashlib.sha256(data[b0:b1]).hexdigest()
    assert expected_sha == sup.snippet_sha256
