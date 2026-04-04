# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from dataclasses import dataclass

from bijux_canon_reason.core.invariants import validate_plan, validate_trace
from bijux_canon_reason.core.types import (
    ClaimType,
    StepKind,
    SupportKind,
    TraceEventKind,
    VerificationCheck,
    VerificationFailure,
    VerificationSeverity,
)
from bijux_canon_reason.verification.context import VerificationContext

INV_SCH_001 = "INV-SCH-001"
INV_LNK_001 = "INV-LNK-001"
INV_ORD_001 = "INV-ORD-001"
INV_TLK_001 = "INV-TLK-001"


@dataclass(frozen=True)
class _TraceStructure:
    claim_ids: set[str]
    evidence_ids: set[str]
    tool_call_ids: set[str]
    finished_step_outputs: set[str]
    has_derived_claim: bool
    has_insufficient_output: bool


def check_core_invariants(
    ctx: VerificationContext,
) -> tuple[VerificationCheck, list[VerificationFailure]]:
    errs = validate_plan(ctx.plan) + validate_trace(ctx.trace, plan=ctx.plan)
    if not errs:
        return VerificationCheck(name="core_invariants", passed=True), []
    details = "\n".join(errs)
    failures = [
        VerificationFailure(
            severity=VerificationSeverity.error,
            message=err,
            invariant_id=INV_SCH_001,
        )
        for err in errs
    ]
    return (
        VerificationCheck(name="core_invariants", passed=False, details=details),
        failures,
    )


def check_claim_supports(
    ctx: VerificationContext,
) -> tuple[VerificationCheck, list[VerificationFailure]]:
    failures: list[VerificationFailure] = []
    trace_structure = _index_trace_structure(ctx)

    for event in ctx.trace.events:
        if event.kind != TraceEventKind.claim_emitted:
            continue
        for support in event.claim.supports:
            if (
                support.kind == SupportKind.claim
                and support.ref_id not in trace_structure.claim_ids
            ):
                failures.append(
                    _failure(
                        message=f"claim_justifications: unknown claim ref {support.ref_id}",
                        invariant_id=INV_LNK_001,
                    )
                )
            if (
                support.kind == SupportKind.evidence
                and support.ref_id not in trace_structure.evidence_ids
            ):
                failures.append(
                    _failure(
                        message=f"claim_justifications: unknown evidence ref {support.ref_id}",
                        invariant_id=INV_LNK_001,
                    )
                )
            if (
                support.kind == SupportKind.tool_call
                and support.ref_id not in trace_structure.tool_call_ids
            ):
                failures.append(
                    _failure(
                        message=f"claim_justifications: unknown tool ref {support.ref_id}",
                        invariant_id=INV_LNK_001,
                    )
                )
    return VerificationCheck(
        name="claim_justifications",
        passed=(len(failures) == 0),
    ), failures


def check_finalize_validated(
    ctx: VerificationContext,
) -> tuple[VerificationCheck, list[VerificationFailure]]:
    finalize_present = "finalize" in _index_trace_structure(ctx).finished_step_outputs
    if finalize_present:
        return VerificationCheck(name="finalize_present", passed=True), []
    return VerificationCheck(name="finalize_present", passed=False), [
        _failure(message="Missing finalize output", invariant_id=INV_ORD_001)
    ]


def check_insufficient_reasoning(
    ctx: VerificationContext,
) -> tuple[VerificationCheck, list[VerificationFailure]]:
    failures: list[VerificationFailure] = []
    trace_structure = _index_trace_structure(ctx)
    has_claim = trace_structure.has_derived_claim
    has_insuff = trace_structure.has_insufficient_output
    if not has_claim and not has_insuff:
        failures.append(
            _failure(message="No derived claims and no insufficiency marker present")
        )
    if has_claim and has_insuff:
        failures.append(
            _failure(message="Both derived claims and insufficiency present (ambiguous)")
        )
    return VerificationCheck(
        name="insufficient_reasoning",
        passed=(len(failures) == 0),
    ), failures


def check_required_steps(
    ctx: VerificationContext,
) -> tuple[VerificationCheck, list[VerificationFailure]]:
    required: set[StepKind] = {"understand", "gather", "derive", "verify", "finalize"}
    trace_structure = _index_trace_structure(ctx)
    seen: set[StepKind] = {
        "derive" if output == "insufficient_evidence" else output
        for output in trace_structure.finished_step_outputs
    }
    missing = sorted(required - seen)
    if not missing:
        return VerificationCheck(name="required_steps", passed=True), []
    msg = f"Missing required step outputs: {missing}"
    return VerificationCheck(name="required_steps", passed=False, details=msg), [
        _failure(message=msg, invariant_id=INV_ORD_001)
    ]


def check_tool_linkage(
    ctx: VerificationContext,
) -> tuple[VerificationCheck, list[VerificationFailure]]:
    tool_call_ids = {
        event.call.id
        for event in ctx.trace.events
        if event.kind == TraceEventKind.tool_called
    }
    tool_result_ids = {
        event.result.call_id
        for event in ctx.trace.events
        if event.kind == TraceEventKind.tool_returned
    }
    missing = sorted(tool_call_ids - tool_result_ids)
    if not missing:
        return VerificationCheck(name="tool_linkage", passed=True), []
    msg = f"tool_linkage: Missing tool results for call ids: {missing}"
    return VerificationCheck(name="tool_linkage", passed=False, details=msg), [
        _failure(message=msg, invariant_id=INV_TLK_001)
    ]


def _index_trace_structure(ctx: VerificationContext) -> _TraceStructure:
    claim_ids: set[str] = set()
    evidence_ids: set[str] = set()
    tool_call_ids: set[str] = set()
    finished_step_outputs: set[str] = set()
    has_derived_claim = False
    has_insufficient_output = False

    for event in ctx.trace.events:
        if event.kind == TraceEventKind.claim_emitted:
            claim_ids.add(event.claim.id)
            has_derived_claim = has_derived_claim or (
                getattr(event.claim, "claim_type", None) == ClaimType.derived
            )
        elif event.kind == TraceEventKind.evidence_registered:
            evidence_ids.add(event.evidence.id)
        elif event.kind == TraceEventKind.tool_returned:
            tool_call_ids.add(event.result.call_id)
        elif event.kind == TraceEventKind.step_finished:
            finished_step_outputs.add(event.output.type)
            has_insufficient_output = (
                has_insufficient_output or event.output.type == "insufficient_evidence"
            )

    return _TraceStructure(
        claim_ids=claim_ids,
        evidence_ids=evidence_ids,
        tool_call_ids=tool_call_ids,
        finished_step_outputs=finished_step_outputs,
        has_derived_claim=has_derived_claim,
        has_insufficient_output=has_insufficient_output,
    )


def _failure(
    *,
    message: str,
    invariant_id: str | None = None,
) -> VerificationFailure:
    return VerificationFailure(
        severity=VerificationSeverity.error,
        message=message,
        invariant_id=invariant_id,
    )


__all__ = [
    "INV_LNK_001",
    "INV_ORD_001",
    "INV_SCH_001",
    "INV_TLK_001",
    "check_claim_supports",
    "check_core_invariants",
    "check_finalize_validated",
    "check_insufficient_reasoning",
    "check_required_steps",
    "check_tool_linkage",
]
