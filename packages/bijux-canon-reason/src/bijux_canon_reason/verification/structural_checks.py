# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

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
    known_claims = {
        event.claim.id
        for event in ctx.trace.events
        if event.kind == TraceEventKind.claim_emitted
    }
    known_evidence = {
        event.evidence.id
        for event in ctx.trace.events
        if event.kind == TraceEventKind.evidence_registered
    }
    known_calls = {
        event.result.call_id
        for event in ctx.trace.events
        if event.kind == TraceEventKind.tool_returned
    }

    for event in ctx.trace.events:
        if event.kind != TraceEventKind.claim_emitted:
            continue
        for support in event.claim.supports:
            if support.kind == SupportKind.claim and support.ref_id not in known_claims:
                failures.append(
                    VerificationFailure(
                        severity=VerificationSeverity.error,
                        message=(
                            f"claim_justifications: unknown claim ref {support.ref_id}"
                        ),
                        invariant_id=INV_LNK_001,
                    )
                )
            if (
                support.kind == SupportKind.evidence
                and support.ref_id not in known_evidence
            ):
                failures.append(
                    VerificationFailure(
                        severity=VerificationSeverity.error,
                        message=(
                            "claim_justifications: unknown evidence ref "
                            f"{support.ref_id}"
                        ),
                        invariant_id=INV_LNK_001,
                    )
                )
            if (
                support.kind == SupportKind.tool_call
                and support.ref_id not in known_calls
            ):
                failures.append(
                    VerificationFailure(
                        severity=VerificationSeverity.error,
                        message=(
                            f"claim_justifications: unknown tool ref {support.ref_id}"
                        ),
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
    finalize_present = any(
        event.kind == TraceEventKind.step_finished and event.output.type == "finalize"
        for event in ctx.trace.events
    )
    if finalize_present:
        return VerificationCheck(name="finalize_present", passed=True), []
    return VerificationCheck(name="finalize_present", passed=False), [
        VerificationFailure(
            severity=VerificationSeverity.error,
            message="Missing finalize output",
            invariant_id=INV_ORD_001,
        )
    ]


def check_insufficient_reasoning(
    ctx: VerificationContext,
) -> tuple[VerificationCheck, list[VerificationFailure]]:
    failures: list[VerificationFailure] = []
    has_claim = any(
        event.kind == TraceEventKind.claim_emitted
        and getattr(event.claim, "claim_type", None) == ClaimType.derived
        for event in ctx.trace.events
    )
    has_insuff = any(
        event.kind == TraceEventKind.step_finished
        and getattr(event.output, "type", "") == "insufficient_evidence"
        for event in ctx.trace.events
    )
    if not has_claim and not has_insuff:
        failures.append(
            VerificationFailure(
                severity=VerificationSeverity.error,
                message="No derived claims and no insufficiency marker present",
            )
        )
    if has_claim and has_insuff:
        failures.append(
            VerificationFailure(
                severity=VerificationSeverity.error,
                message="Both derived claims and insufficiency present (ambiguous)",
            )
        )
    return VerificationCheck(
        name="insufficient_reasoning",
        passed=(len(failures) == 0),
    ), failures


def check_required_steps(
    ctx: VerificationContext,
) -> tuple[VerificationCheck, list[VerificationFailure]]:
    required: set[StepKind] = {"understand", "gather", "derive", "verify", "finalize"}
    seen: set[StepKind] = set()
    for event in ctx.trace.events:
        if event.kind != TraceEventKind.step_finished:
            continue
        out_type = event.output.type
        if out_type == "insufficient_evidence":
            seen.add("derive")
        else:
            seen.add(out_type)
    missing = sorted(required - seen)
    if not missing:
        return VerificationCheck(name="required_steps", passed=True), []
    msg = f"Missing required step outputs: {missing}"
    return VerificationCheck(name="required_steps", passed=False, details=msg), [
        VerificationFailure(
            severity=VerificationSeverity.error,
            message=msg,
            invariant_id=INV_ORD_001,
        )
    ]


def check_tool_linkage(
    ctx: VerificationContext,
) -> tuple[VerificationCheck, list[VerificationFailure]]:
    calls: list[str] = []
    results: set[str] = set()
    for event in ctx.trace.events:
        if event.kind == TraceEventKind.tool_called:
            calls.append(event.call.id)
        if event.kind == TraceEventKind.tool_returned:
            results.add(event.result.call_id)
    missing = sorted(set(calls) - results)
    if not missing:
        return VerificationCheck(name="tool_linkage", passed=True), []
    msg = f"tool_linkage: Missing tool results for call ids: {missing}"
    return VerificationCheck(name="tool_linkage", passed=False, details=msg), [
        VerificationFailure(
            severity=VerificationSeverity.error,
            message=msg,
            invariant_id=INV_TLK_001,
        )
    ]


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
