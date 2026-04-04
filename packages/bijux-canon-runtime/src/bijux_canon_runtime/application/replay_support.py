"""Replay diff helpers for semantic payloads and normalization."""

from __future__ import annotations

from collections.abc import Iterable

from bijux_canon_runtime.model.artifact.artifact import Artifact
from bijux_canon_runtime.model.artifact.retrieved_evidence import RetrievedEvidence
from bijux_canon_runtime.model.datasets.dataset_descriptor import DatasetDescriptor
from bijux_canon_runtime.model.execution.replay_envelope import ReplayEnvelope
from bijux_canon_runtime.observability.classification.fingerprint import (
    fingerprint_inputs,
)
from bijux_canon_runtime.ontology.public import ReplayAcceptability


def semantic_artifact_fingerprint(artifacts: Iterable[Artifact]) -> str:
    """Fingerprint artifacts for replay comparison."""
    normalized = sorted(
        artifacts,
        key=lambda item: (
            str(item.tenant_id),
            str(item.artifact_id),
            str(item.content_hash),
        ),
    )
    return fingerprint_inputs(
        [
            {
                "tenant_id": item.tenant_id,
                "artifact_id": item.artifact_id,
                "content_hash": item.content_hash,
            }
            for item in normalized
        ]
    )


def semantic_evidence_fingerprint(evidence: Iterable[RetrievedEvidence]) -> str:
    """Fingerprint evidence for replay comparison."""
    normalized = sorted(
        evidence,
        key=lambda item: (str(item.evidence_id), str(item.content_hash)),
    )
    return fingerprint_inputs(
        [
            {
                "evidence_id": item.evidence_id,
                "content_hash": item.content_hash,
                "determinism": item.determinism,
            }
            for item in normalized
        ]
    )


def partition_diffs(
    diffs: dict[str, object], acceptability: ReplayAcceptability
) -> tuple[dict[str, object], dict[str, object]]:
    """Partition replay diffs into blocking and policy-acceptable sets."""
    if not diffs:
        return {}, {}
    allowed: set[str] = set()
    if acceptability in {
        ReplayAcceptability.INVARIANT_PRESERVING,
        ReplayAcceptability.STATISTICALLY_BOUNDED,
    }:
        allowed = {
            "events",
            "artifact_fingerprint",
            "artifact_count",
            "evidence_fingerprint",
            "evidence_count",
        }
    blocking = {key: value for key, value in diffs.items() if key not in allowed}
    acceptable = {key: value for key, value in diffs.items() if key in allowed}
    return blocking, acceptable


def dataset_payload(dataset: DatasetDescriptor) -> dict[str, object]:
    """Serialize dataset descriptor fields used in replay diffs."""
    return {
        "dataset_id": dataset.dataset_id,
        "tenant_id": dataset.tenant_id,
        "dataset_version": dataset.dataset_version,
        "dataset_hash": dataset.dataset_hash,
        "dataset_state": dataset.dataset_state,
        "storage_uri": dataset.storage_uri,
    }


def envelope_payload(envelope: ReplayEnvelope) -> dict[str, object]:
    """Serialize replay-envelope fields used in replay diffs."""
    return {
        "min_claim_overlap": envelope.min_claim_overlap,
        "max_contradiction_delta": envelope.max_contradiction_delta,
    }


__all__ = [
    "dataset_payload",
    "envelope_payload",
    "partition_diffs",
    "semantic_artifact_fingerprint",
    "semantic_evidence_fingerprint",
]
