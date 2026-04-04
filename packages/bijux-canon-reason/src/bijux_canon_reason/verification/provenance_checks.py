# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re

from bijux_canon_reason.core.types import (
    ClaimType,
    JsonValue,
    SupportKind,
    TraceEventKind,
    VerificationCheck,
    VerificationFailure,
    VerificationSeverity,
)
from bijux_canon_reason.verification.context import VerificationContext

INV_GRD_001 = "INV-GRD-001"
INV_GRD_002 = "INV-GRD-002"
INV_EVD_001 = "INV-EVD-001"
EVIDENCE_MARKER_RE = re.compile(
    r"\[evidence:(?P<eid>[^:\]]+):(?P<b0>\d+)-(?P<b1>\d+):(?P<sha>[0-9a-f]{64})\]"
)


@dataclass(frozen=True)
class _ChunkManifest:
    spans: dict[str, tuple[int, int]]
    hashes: dict[str, str]


@dataclass(frozen=True)
class _EvidenceArtifact:
    bytes_: bytes
    span: tuple[int, int]


def check_derived_grounding(
    ctx: VerificationContext,
) -> tuple[VerificationCheck, list[VerificationFailure]]:
    """Derived claims must be grounded in evidence with canonical span and hash citations."""
    failures: list[VerificationFailure] = []
    min_supports = _resolve_min_supports(_reasoning_policy(ctx))
    for event in ctx.trace.events:
        if event.kind != TraceEventKind.claim_emitted:
            continue
        claim = event.claim
        if getattr(claim, "claim_type", None) != ClaimType.derived:
            continue

        evidence_supports = _evidence_supports(claim.supports)
        if not evidence_supports:
            failures.append(
                _failure(
                    message=(
                        f"derived_claim_grounding: claim {claim.id} has no evidence supports"
                    ),
                    invariant_id=INV_GRD_001,
                )
            )
            continue
        if len(evidence_supports) < min_supports:
            failures.append(
                _failure(
                    message=(
                        f"derived_claim_grounding: claim {claim.id} has "
                        f"{len(evidence_supports)} supports < required {min_supports}"
                    ),
                    invariant_id=INV_GRD_002,
                )
            )

        marker_map = _marker_map(claim.statement or "")
        for support in evidence_supports:
            start, end = support.span
            marker_key = (support.ref_id, start, end, support.snippet_sha256)
            if marker_key not in marker_map:
                failures.append(
                    _failure(
                        message=(
                            "derived_claim_grounding: claim "
                            f"{claim.id} missing canonical citation marker "
                            f"[evidence:{support.ref_id}:{start}-{end}:{support.snippet_sha256}]"
                        ),
                        invariant_id=INV_GRD_001,
                    )
                )

        for evidence_id, start, end, sha in marker_map:
            if not any(
                support.ref_id == evidence_id
                and support.span == (start, end)
                and support.snippet_sha256 == sha
                for support in evidence_supports
            ):
                failures.append(
                    _failure(
                        message=(
                            f"derived_claim_grounding: marker for evidence {evidence_id} "
                            "has no matching support"
                        ),
                        invariant_id=INV_GRD_001,
                    )
                )

    return VerificationCheck(
        name="derived_claim_grounding",
        passed=(len(failures) == 0),
    ), failures


def check_evidence_hashes(
    ctx: VerificationContext,
) -> tuple[VerificationCheck, list[VerificationFailure]]:
    if ctx.artifacts_dir is None:
        return VerificationCheck(
            name="evidence_hashes",
            passed=True,
            details="skipped (no artifacts_dir)",
        ), []

    failures: list[VerificationFailure] = []
    for event in ctx.trace.events:
        if event.kind != TraceEventKind.evidence_registered:
            continue
        reference = event.evidence
        abs_path = _resolve_under_root(ctx.artifacts_dir, reference.content_path)
        if abs_path is None:
            failures.append(
                _failure(
                    message=f"Evidence path escapes artifacts_dir: {reference.content_path}",
                    invariant_id=INV_EVD_001,
                )
            )
            continue
        if not abs_path.exists():
            failures.append(
                _failure(
                    message=f"Missing evidence file: {reference.content_path}",
                    invariant_id=INV_EVD_001,
                )
            )
            continue
        if _sha256_path(abs_path) != reference.sha256:
            failures.append(
                _failure(
                    message=f"Evidence {reference.id} sha256 mismatch",
                    invariant_id=INV_EVD_001,
                )
            )
    return VerificationCheck(
        name="evidence_hashes",
        passed=(len(failures) == 0),
    ), failures


def check_support_spans(
    ctx: VerificationContext,
) -> tuple[VerificationCheck, list[VerificationFailure]]:
    """Ensure evidence supports carry valid spans and snippet hashes."""
    if ctx.artifacts_dir is None:
        return VerificationCheck(
            name="support_spans",
            passed=True,
            details="skipped (no artifacts_dir)",
        ), []

    failures: list[VerificationFailure] = []
    chunk_manifest = _load_chunk_manifest(ctx.artifacts_dir)
    evidence_artifacts = _load_evidence_artifacts(
        ctx=ctx,
        chunk_manifest=chunk_manifest,
        failures=failures,
    )

    for event in ctx.trace.events:
        if event.kind != TraceEventKind.claim_emitted:
            continue
        for support in event.claim.supports:
            if support.kind != SupportKind.evidence:
                continue
            _validate_support_span(
                claim_id=event.claim.id,
                support=support,
                evidence_artifacts=evidence_artifacts,
                failures=failures,
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
        event.kind == TraceEventKind.claim_emitted
        and getattr(event.claim, "claim_type", None) == ClaimType.derived
        for event in ctx.trace.events
    )
    if not has_claim:
        return VerificationCheck(name="reasoning_trace", passed=True), []

    metadata = ctx.trace.metadata if isinstance(ctx.trace.metadata, dict) else {}
    reasoning_meta = (
        metadata.get("reasoning_trace") if isinstance(metadata, dict) else None
    )
    if not isinstance(reasoning_meta, dict):
        failures.append(_failure(message="reasoning_trace: missing reasoning metadata"))
        return VerificationCheck(name="reasoning_trace", passed=False), failures

    expected_hash = reasoning_meta.get("reasoning_trace_sha256")
    if not isinstance(expected_hash, str) or len(expected_hash) != 64:
        failures.append(_failure(message="reasoning_trace: missing result hash"))
        return VerificationCheck(name="reasoning_trace", passed=False), failures

    claim_hashes = _derived_claim_hashes(ctx=ctx, failures=failures)
    if not claim_hashes and failures:
        return VerificationCheck(name="reasoning_trace", passed=False), failures
    if not claim_hashes:
        failures.append(
            _failure(message="reasoning_trace: no derived claim hashes found")
        )
        return VerificationCheck(name="reasoning_trace", passed=False), failures
    if len(claim_hashes) != 1:
        failures.append(
            _failure(message="reasoning_trace: multiple result hashes present")
        )
        return VerificationCheck(name="reasoning_trace", passed=False), failures
    if next(iter(claim_hashes)) != expected_hash:
        failures.append(_failure(message="reasoning_trace: metadata hash mismatch"))
    return VerificationCheck(
        name="reasoning_trace",
        passed=(len(failures) == 0),
    ), failures


def _sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _reasoning_policy(ctx: VerificationContext) -> dict[str, JsonValue]:
    metadata = ctx.trace.metadata if isinstance(ctx.trace.metadata, dict) else {}
    policy = metadata.get("reasoning_policy", {}) if isinstance(metadata, dict) else {}
    return policy if isinstance(policy, dict) else {}


def _resolve_min_supports(policy: dict[str, JsonValue]) -> int:
    raw_min = policy.get("min_supports_per_claim")
    if not isinstance(raw_min, (int, float, str)):
        return 2
    try:
        return max(1, int(raw_min))
    except ValueError:
        return 1


def _marker_map(statement: str) -> set[tuple[str, int, int, str]]:
    return {
        (
            match.group("eid"),
            int(match.group("b0")),
            int(match.group("b1")),
            match.group("sha"),
        )
        for match in EVIDENCE_MARKER_RE.finditer(statement)
    }


def _load_chunk_manifest(
    artifacts_dir: Path,
) -> _ChunkManifest:
    chunk_spans: dict[str, tuple[int, int]] = {}
    chunk_hashes: dict[str, str] = {}
    chunks_file = artifacts_dir / "provenance" / "chunks.jsonl"
    if not chunks_file.exists():
        return _ChunkManifest(spans=chunk_spans, hashes=chunk_hashes)

    for line in chunks_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        chunk_id = str(obj.get("chunk_id", ""))
        if not chunk_id or "start_byte" not in obj or "end_byte" not in obj:
            continue
        chunk_spans[chunk_id] = (int(obj["start_byte"]), int(obj["end_byte"]))
        if "chunk_sha256" in obj:
            chunk_hashes[chunk_id] = str(obj["chunk_sha256"])
    return _ChunkManifest(spans=chunk_spans, hashes=chunk_hashes)


def _derived_claim_hashes(
    *,
    ctx: VerificationContext,
    failures: list[VerificationFailure],
) -> set[str]:
    claim_hashes: set[str] = set()
    for event in ctx.trace.events:
        if (
            event.kind != TraceEventKind.claim_emitted
            or getattr(event.claim, "claim_type", None) != ClaimType.derived
        ):
            continue
        structured = (
            event.claim.structured if isinstance(event.claim.structured, dict) else {}
        )
        result_hash = (
            structured.get("result_sha256") if isinstance(structured, dict) else None
        )
        if isinstance(result_hash, str) and len(result_hash) == 64:
            claim_hashes.add(result_hash)
            continue
        failures.append(
            _failure(
                message=f"reasoning_trace: claim {event.claim.id} missing result_sha256"
            )
        )
    return claim_hashes


def _load_evidence_artifacts(
    *,
    ctx: VerificationContext,
    chunk_manifest: _ChunkManifest,
    failures: list[VerificationFailure],
) -> dict[str, _EvidenceArtifact]:
    artifacts: dict[str, _EvidenceArtifact] = {}
    for event in ctx.trace.events:
        if event.kind != TraceEventKind.evidence_registered:
            continue
        abs_path = _resolve_under_root(ctx.artifacts_dir, event.evidence.content_path)
        if abs_path is None or not abs_path.exists():
            continue
        bytes_ = abs_path.read_bytes()
        artifacts[event.evidence.id] = _EvidenceArtifact(
            bytes_=bytes_,
            span=(int(event.evidence.span[0]), int(event.evidence.span[1])),
        )
        _validate_chunk_alignment(
            event=event,
            abs_path=abs_path,
            chunk_manifest=chunk_manifest,
            failures=failures,
        )
    return artifacts


def _resolve_under_root(root: Path, rel_posix_path: str) -> Path | None:
    """Resolve rel_posix_path under root, rejecting traversal and escape."""
    try:
        root_resolved = root.resolve(strict=True)
        candidate = (root_resolved / rel_posix_path).resolve(strict=True)
        candidate.relative_to(root_resolved)
        return candidate
    except (FileNotFoundError, OSError, ValueError):
        return None


def _validate_chunk_alignment(
    *,
    event: object,
    abs_path: Path,
    chunk_manifest: _ChunkManifest,
    failures: list[VerificationFailure],
) -> None:
    evidence = event.evidence
    if evidence.chunk_id not in chunk_manifest.spans:
        return
    chunk_span = chunk_manifest.spans[evidence.chunk_id]
    if tuple(evidence.span) != tuple(chunk_span):
        failures.append(
            _failure(
                message=(
                    f"support_spans: evidence span {evidence.span} does not"
                    f" match chunk span {chunk_span} for chunk {evidence.chunk_id}"
                ),
                invariant_id=INV_EVD_001,
            )
        )
        return
    if evidence.chunk_id in chunk_manifest.hashes and (
        hashlib.sha256(abs_path.read_bytes()).hexdigest()
        != chunk_manifest.hashes[evidence.chunk_id]
    ):
        failures.append(
            _failure(
                message=(
                    "support_spans: evidence hash mismatch vs chunk hash"
                    f" for {evidence.chunk_id}"
                ),
                invariant_id=INV_EVD_001,
            )
        )


def _validate_support_span(
    *,
    claim_id: str,
    support: object,
    evidence_artifacts: dict[str, _EvidenceArtifact],
    failures: list[VerificationFailure],
) -> None:
    artifact = evidence_artifacts.get(support.ref_id)
    if artifact is None:
        failures.append(
            _failure(
                message=(
                    f"support_spans: evidence {support.ref_id} bytes missing for"
                    f" claim {claim_id}"
                ),
                invariant_id=INV_EVD_001,
            )
        )
        return
    start, end = support.span
    data = artifact.bytes_
    if start < 0 or end > len(data) or start >= end:
        failures.append(
            _failure(
                message=(
                    f"support_spans: invalid span {support.span} for evidence"
                    f" {support.ref_id} in claim {claim_id}"
                ),
                invariant_id=INV_EVD_001,
            )
        )
        return
    evidence_start, evidence_end = artifact.span
    if start < evidence_start or end > evidence_end:
        failures.append(
            _failure(
                message=(
                    f"support_spans: support span {support.span} not within "
                    f"evidence span {artifact.span} for {support.ref_id}"
                ),
                invariant_id=INV_EVD_001,
            )
        )
        return
    snippet_hash = hashlib.sha256(data[start:end]).hexdigest()
    if snippet_hash != support.snippet_sha256:
        failures.append(
            _failure(
                message=(
                    f"support_spans: snippet hash mismatch for evidence"
                    f" {support.ref_id} in claim {claim_id}"
                ),
                invariant_id=INV_EVD_001,
            )
        )


def _evidence_supports(supports: list[object]) -> list[object]:
    return [support for support in supports if support.kind == SupportKind.evidence]


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
    "INV_EVD_001",
    "INV_GRD_001",
    "INV_GRD_002",
    "check_derived_grounding",
    "check_evidence_hashes",
    "check_reasoning_trace",
    "check_support_spans",
]
