# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from pathlib import Path

import pytest

from bijux_rar.boundaries.serde.json_canonical import canonical_json_line
from bijux_rar.boundaries.serde.trace_jsonl import read_trace_jsonl, write_trace_jsonl
from bijux_rar.core.fingerprints import fingerprint_obj
from bijux_rar.core.rar_types import (
    Claim,
    ClaimEmittedEvent,
    ClaimStatus,
    ClaimType,
    DeriveOutput,
    Plan,
    PlanNode,
    ProblemSpec,
    StepFinishedEvent,
    StepSpec,
    StepStartedEvent,
    Trace,
    TraceEventKind,
)


def test_trace_jsonl_roundtrip_is_stable(tmp_path: Path) -> None:
    spec = ProblemSpec(description="Trace roundtrip")
    n1 = PlanNode(kind="understand", dependencies=[], step=StepSpec(kind="understand"))
    assert spec.id is not None
    assert n1.id is not None
    plan = Plan(spec_id=spec.id, nodes=[n1])

    claim = Claim(
        claim_type=ClaimType.derived,
        statement="x",
        structured={"x": 1},
        status=ClaimStatus.proposed,
        confidence=1.0,
        support_refs=[],
    )

    assert claim.id is not None
    cid = claim.id

    events = [
        StepStartedEvent(idx=0, kind=TraceEventKind.step_started, step_id=n1.id),
        ClaimEmittedEvent(idx=1, kind=TraceEventKind.claim_emitted, claim=claim),
        StepFinishedEvent(
            idx=2,
            kind=TraceEventKind.step_finished,
            step_id=n1.id,
            output=DeriveOutput(kind="derive", emitted_claim_ids=[cid]),
        ),
    ]

    assert plan.id is not None
    trace = Trace(spec_id=spec.id, plan_id=plan.id, events=events, metadata={"seed": 1})

    out = tmp_path / "trace.jsonl"
    write_trace_jsonl(trace, out)

    trace2 = read_trace_jsonl(out)

    assert fingerprint_obj(trace.model_dump(mode="json")) == fingerprint_obj(
        trace2.model_dump(mode="json")
    )


def test_canonical_json_line_orders_keys() -> None:
    left = canonical_json_line({"b": 1, "a": 2})
    right = canonical_json_line({"a": 2, "b": 1})
    assert left == right


def test_read_trace_jsonl_rejects_bad_header(tmp_path: Path) -> None:
    path = tmp_path / "bad.jsonl"
    path.write_text('{"record":"not_header"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="trace_header"):
        read_trace_jsonl(path)
