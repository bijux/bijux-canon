# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

from bijux_canon_reason.core.types import (
    ClaimType,
    JsonValue,
    SupportKind,
    Trace,
    TraceEventKind,
    VerificationCheck,
    VerificationFailure,
    VerificationSeverity,
)
from bijux_canon_reason.verification.context import VerificationContext
from bijux_canon_reason.verification.structural_checks import (
    check_claim_supports,
    check_core_invariants,
    check_finalize_validated,
    check_insufficient_reasoning,
    check_required_steps,
    check_tool_linkage,
)

INV_GRD_001 = "INV-GRD-001"
INV_GRD_002 = "INV-GRD-002"
INV_EVD_001 = "INV-EVD-001"


def _sha256_path(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _resolve_under_root(root: Path, rel_posix_path: str) -> Path | None:
    """Resolve rel_posix_path under root, rejecting traversal/escape."""
    try:
        root_r = root.resolve(strict=True)
        cand = (root_r / rel_posix_path).resolve(strict=True)
        cand.relative_to(root_r)
        return cand
    except Exception:  # noqa: BLE001
        return None


def check_derived_grounding(
    ctx: VerificationContext,
) -> tuple[VerificationCheck, list[VerificationFailure]]:
    """Derived claims must be grounded in evidence with canonical span+hash citations."""
    failures: list[VerificationFailure] = []
    policy = (
        ctx.trace.metadata.get("reasoning_policy", {})
        if isinstance(ctx.trace.metadata, dict)
        else {}
    )
    raw_min: JsonValue | None = None
    if isinstance(policy, dict):
        val = policy.get("min_supports_per_claim")
        raw_min = val if isinstance(val, (int, float, str)) else None
    min_supports = 2
    if raw_min is not None and isinstance(raw_min, (int, float, str)):
        try:
            min_supports = max(1, int(raw_min))
        except Exception:  # noqa: BLE001
            min_supports = 1
    marker_re = re.compile(
        r"\[evidence:(?P<eid>[^:\]]+):(?P<b0>\d+)-(?P<b1>\d+):(?P<sha>[0-9a-f]{64})\]"
    )
    for ev in ctx.trace.events:
        if ev.kind != TraceEventKind.claim_emitted:
            continue
        claim = ev.claim
        if getattr(claim, "claim_type", None) != ClaimType.derived:
            continue

        ev_supports = [s for s in claim.supports if s.kind == SupportKind.evidence]
        if not ev_supports:
            failures.append(
                VerificationFailure(
                    severity=VerificationSeverity.error,
                    message=(
                        f"derived_claim_grounding: claim {claim.id} has no evidence supports"
                    ),
                    invariant_id=INV_GRD_001,
                )
            )
            continue
        if len(ev_supports) < min_supports:
            failures.append(
                VerificationFailure(
                    severity=VerificationSeverity.error,
                    message=(
                        f"derived_claim_grounding: claim {claim.id} has "
                        f"{len(ev_supports)} supports < required {min_supports}"
                    ),
                    invariant_id=INV_GRD_002,
                )
            )

        stmt = claim.statement or ""
        markers = list(marker_re.finditer(stmt))
        marker_map = {
            (m.group("eid"), int(m.group("b0")), int(m.group("b1")), m.group("sha"))
            for m in markers
        }

        for sup in ev_supports:
            b0, b1 = sup.span
            key = (sup.ref_id, b0, b1, sup.snippet_sha256)
            if key not in marker_map:
                failures.append(
                    VerificationFailure(
                        severity=VerificationSeverity.error,
                        message=(
                            "derived_claim_grounding: claim "
                            f"{claim.id} missing canonical citation marker "
                            f"[evidence:{sup.ref_id}:{b0}-{b1}:{sup.snippet_sha256}]"
                        ),
                        invariant_id=INV_GRD_001,
                    )
                )

        for mk in marker_map:
            eid, b0, b1, sha = mk
            if not any(
                s.ref_id == eid and s.span == (b0, b1) and s.snippet_sha256 == sha
                for s in ev_supports
            ):
                failures.append(
                    VerificationFailure(
                        severity=VerificationSeverity.error,
                        message=(
                            f"derived_claim_grounding: marker for evidence {eid} "
                            "has no matching support"
                        ),
                        invariant_id=INV_GRD_001,
                    )
                )

    passed = len(failures) == 0
    return VerificationCheck(name="derived_claim_grounding", passed=passed), failures
def check_evidence_hashes(
    ctx: VerificationContext,
) -> tuple[VerificationCheck, list[VerificationFailure]]:
    if ctx.artifacts_dir is None:
        return VerificationCheck(
            name="evidence_hashes", passed=True, details="skipped (no artifacts_dir)"
        ), []

    failures: list[VerificationFailure] = []
    for ev in ctx.trace.events:
        if ev.kind != TraceEventKind.evidence_registered:
            continue
        ref = ev.evidence
        abs_path = _resolve_under_root(ctx.artifacts_dir, ref.content_path)
        if abs_path is None:
            failures.append(
                VerificationFailure(
                    severity=VerificationSeverity.error,
                    message=f"Evidence path escapes artifacts_dir: {ref.content_path}",
                    invariant_id=INV_EVD_001,
                )
            )
            continue
        if not abs_path.exists():
            failures.append(
                VerificationFailure(
                    severity=VerificationSeverity.error,
                    message=f"Missing evidence file: {ref.content_path}",
                    invariant_id=INV_EVD_001,
                )
            )
            continue
        got = _sha256_path(abs_path)
        if got != ref.sha256:
            failures.append(
                VerificationFailure(
                    severity=VerificationSeverity.error,
                    message=f"Evidence {ref.id} sha256 mismatch",
                    invariant_id=INV_EVD_001,
                )
            )
    return VerificationCheck(
        name="evidence_hashes", passed=(len(failures) == 0)
    ), failures


def check_support_spans(
    ctx: VerificationContext,
) -> tuple[VerificationCheck, list[VerificationFailure]]:
    """Ensure evidence supports carry valid spans and snippet hashes."""
    if ctx.artifacts_dir is None:
        return VerificationCheck(
            name="support_spans", passed=True, details="skipped (no artifacts_dir)"
        ), []

    failures: list[VerificationFailure] = []
    evidence_bytes: dict[str, bytes] = {}
    evidence_spans: dict[str, tuple[int, int]] = {}
    chunk_spans: dict[str, tuple[int, int]] = {}
    chunk_hashes: dict[str, str] = {}
    chunks_file = ctx.artifacts_dir / "provenance" / "chunks.jsonl"
    if chunks_file.exists():
        for line in chunks_file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            cid = str(obj.get("chunk_id", ""))
            if cid and "start_byte" in obj and "end_byte" in obj:
                b0 = int(obj["start_byte"])
                b1 = int(obj["end_byte"])
                chunk_spans[cid] = (b0, b1)
                if "chunk_sha256" in obj:
                    chunk_hashes[cid] = str(obj["chunk_sha256"])
    for ev in ctx.trace.events:
        if ev.kind != TraceEventKind.evidence_registered:
            continue
        abs_path = _resolve_under_root(ctx.artifacts_dir, ev.evidence.content_path)
        if abs_path is None or not abs_path.exists():
            continue
        evidence_bytes[ev.evidence.id] = abs_path.read_bytes()
        evidence_spans[ev.evidence.id] = (
            int(ev.evidence.span[0]),
            int(ev.evidence.span[1]),
        )
        if ev.evidence.chunk_id in chunk_spans:
            c_span = chunk_spans[ev.evidence.chunk_id]
            if tuple(ev.evidence.span) != tuple(c_span):
                failures.append(
                    VerificationFailure(
                        severity=VerificationSeverity.error,
                        message=(
                            f"support_spans: evidence span {ev.evidence.span} does not"
                            f" match chunk span {c_span} for chunk {ev.evidence.chunk_id}"
                        ),
                        invariant_id=INV_EVD_001,
                    )
                )
            elif ev.evidence.chunk_id in chunk_hashes and (
                hashlib.sha256(abs_path.read_bytes()).hexdigest()
                != chunk_hashes[ev.evidence.chunk_id]
            ):
                failures.append(
                    VerificationFailure(
                        severity=VerificationSeverity.error,
                        message=(
                            f"support_spans: evidence hash mismatch vs chunk hash"
                            f" for {ev.evidence.chunk_id}"
                        ),
                        invariant_id=INV_EVD_001,
                    )
                )

    for ev in ctx.trace.events:
        if ev.kind != TraceEventKind.claim_emitted:
            continue
        for sup in ev.claim.supports:
            if sup.kind != SupportKind.evidence:
                continue
            data = evidence_bytes.get(sup.ref_id)
            if data is None:
                failures.append(
                    VerificationFailure(
                        severity=VerificationSeverity.error,
                        message=(
                            f"support_spans: evidence {sup.ref_id} bytes missing for"
                            f" claim {ev.claim.id}"
                        ),
                        invariant_id=INV_EVD_001,
                    )
                )
                continue
            start, end = sup.span
            if start < 0 or end > len(data) or start >= end:
                failures.append(
                    VerificationFailure(
                        severity=VerificationSeverity.error,
                        message=(
                            f"support_spans: invalid span {sup.span} for evidence"
                            f" {sup.ref_id} in claim {ev.claim.id}"
                        ),
                        invariant_id=INV_EVD_001,
                    )
                )
                continue
            ev_span = evidence_spans.get(sup.ref_id)
            if ev_span is not None:
                ev_start, ev_end = ev_span
                if start < ev_start or end > ev_end:
                    failures.append(
                        VerificationFailure(
                            severity=VerificationSeverity.error,
                            message=(
                                f"support_spans: support span {sup.span} not within "
                                f"evidence span {ev_span} for {sup.ref_id}"
                            ),
                            invariant_id=INV_EVD_001,
                        )
                    )
                    continue
            snippet = data[start:end]
            got = hashlib.sha256(snippet).hexdigest()
            if got != sup.snippet_sha256:
                failures.append(
                    VerificationFailure(
                        severity=VerificationSeverity.error,
                        message=(
                            f"support_spans: snippet hash mismatch for evidence"
                            f" {sup.ref_id} in claim {ev.claim.id}"
                        ),
                        invariant_id=INV_EVD_001,
                    )
                )

    return VerificationCheck(
        name="support_spans",
        passed=(len(failures) == 0),
    ), failures


def check_reasoning_trace(
    ctx: VerificationContext,
) -> tuple[VerificationCheck, list[VerificationFailure]]:
    """Ensure reasoning trace hash matches claim payloads and metadata."""
    failures: list[VerificationFailure] = []
    has_claim = any(
        ev.kind == TraceEventKind.claim_emitted
        and getattr(ev.claim, "claim_type", None) == ClaimType.derived
        for ev in ctx.trace.events
    )
    if not has_claim:
        # If no derived claims exist, we skip reasoning hash enforcement; other checks handle insufficiency.
        return VerificationCheck(name="reasoning_trace", passed=True), []
    meta = ctx.trace.metadata if isinstance(ctx.trace.metadata, dict) else {}
    rmeta = meta.get("reasoning_trace") if isinstance(meta, dict) else None
    if not isinstance(rmeta, dict):
        failures.append(
            VerificationFailure(
                severity=VerificationSeverity.error,
                message="reasoning_trace: missing reasoning metadata",
            )
        )
        return VerificationCheck(name="reasoning_trace", passed=False), failures

    expected_hash = rmeta.get("reasoning_trace_sha256")
    if not isinstance(expected_hash, str) or len(expected_hash) != 64:
        failures.append(
            VerificationFailure(
                severity=VerificationSeverity.error,
                message="reasoning_trace: missing result hash",
            )
        )
        return VerificationCheck(name="reasoning_trace", passed=False), failures

    # Gather derived claim hashes.
    claim_hashes: set[str] = set()
    for ev in ctx.trace.events:
        if (
            ev.kind == TraceEventKind.claim_emitted
            and getattr(ev.claim, "claim_type", None) == ClaimType.derived
        ):
            structured = (
                ev.claim.structured if isinstance(ev.claim.structured, dict) else {}
            )
            rhash = (
                structured.get("result_sha256")
                if isinstance(structured, dict)
                else None
            )
            if isinstance(rhash, str) and len(rhash) == 64:
                claim_hashes.add(rhash)
            else:
                failures.append(
                    VerificationFailure(
                        severity=VerificationSeverity.error,
                        message=f"reasoning_trace: claim {ev.claim.id} missing result_sha256",
                    )
                )
    if not claim_hashes:
        failures.append(
            VerificationFailure(
                severity=VerificationSeverity.error,
                message="reasoning_trace: no derived claim hashes found",
            )
        )
        return VerificationCheck(name="reasoning_trace", passed=False), failures

    if len(claim_hashes) != 1:
        failures.append(
            VerificationFailure(
                severity=VerificationSeverity.error,
                message="reasoning_trace: multiple result hashes present",
            )
        )
        return VerificationCheck(name="reasoning_trace", passed=False), failures

    only_hash = next(iter(claim_hashes))
    if only_hash != expected_hash:
        failures.append(
            VerificationFailure(
                severity=VerificationSeverity.error,
                message="reasoning_trace: metadata hash mismatch",
            )
        )
    return VerificationCheck(
        name="reasoning_trace", passed=(len(failures) == 0)
    ), failures
def run_all_checks(
    ctx: VerificationContext,
) -> tuple[list[VerificationCheck], list[VerificationFailure]]:
    checks: list[VerificationCheck] = []
    failures: list[VerificationFailure] = []
    for fn in (
        check_core_invariants,
        check_tool_linkage,
        check_claim_supports,
        check_derived_grounding,
        check_reasoning_trace,
        check_insufficient_reasoning,
        check_finalize_validated,
        check_required_steps,
        check_evidence_hashes,
        check_support_spans,
    ):
        c, f = fn(ctx)
        checks.append(c)
        failures.extend(f)
    return checks, failures
