# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

pytest.importorskip("faiss")

from bijux_canon_index.application import (
    AdmittedIndexChunk,
    IndexBuildLimits,
    IndexCompatibility,
    IndexQueryChannel,
    IndexQueryRequest,
    IndexService,
    VexArtifactStore,
    VexCandidateRecord,
    VexExecutionArtifact,
    VexPolicyDecision,
    VexPolicyStatus,
)
from bijux_canon_index.infra.adapters.faiss.hnsw import HnswParameters


def _chunks() -> tuple[AdmittedIndexChunk, ...]:
    return (
        AdmittedIndexChunk(
            "chunk-a",
            "paper-a",
            0,
            "Ancient DNA preserves direct evidence.",
            (1.0, 0.0, 0.0),
            {"source_id": "paper-a", "language": "en"},
        ),
        AdmittedIndexChunk(
            "chunk-b",
            "paper-b",
            0,
            "Genomic contamination constrains interpretation.",
            (0.0, 1.0, 0.0),
            {"source_id": "paper-b", "language": "en"},
        ),
        AdmittedIndexChunk(
            "chunk-c",
            "paper-c",
            0,
            "Context determines the strength of inference.",
            (0.0, 0.0, 1.0),
            {"source_id": "paper-c", "language": "en"},
        ),
    )


def _assert_reachable(
    record: dict[str, object],
    *,
    admitted_ids: Counter[str],
    generation_id: str,
    model_lock_artifact_id: str,
) -> None:
    request = record["request"]
    witness = record["witness"]
    assert isinstance(request, dict)
    assert isinstance(witness, dict)
    assert request["generation_id"] == generation_id
    assert request["model_lock_artifact_id"] == model_lock_artifact_id
    assert witness["generation_id"] == generation_id
    assert witness["model_lock_artifact_id"] == model_lock_artifact_id

    candidate_order = record["candidate_order"]
    exact_candidates = witness["candidates"]
    assert isinstance(candidate_order, list)
    assert isinstance(exact_candidates, list)
    for candidate in (*candidate_order, *exact_candidates):
        assert isinstance(candidate, dict)
        assert admitted_ids[str(candidate["chunk_id"])] == 1


def test_every_vex_result_resolves_once_and_remains_inspectable_after_restart(
    tmp_path: Path,
) -> None:
    compatibility = IndexCompatibility("sha256:model-lock", 3)
    service = IndexService(tmp_path / "registry", compatibility=compatibility)
    inspection = service.build(
        _chunks(),
        snapshot_artifact_id="sha256:snapshot",
        model_lock_artifact_id="sha256:model-lock",
        limits=IndexBuildLimits(10, 10_000, 10_000, 10_000),
        hnsw_parameters=HnswParameters(m=2, ef_construction=8, ef_search=8, seed=17),
        activate=True,
    )
    request = IndexQueryRequest(
        channel=IndexQueryChannel.dense_hnsw,
        query_vector=(1.0, 0.0, 0.0),
        top_k=3,
    )
    report = service.query(request)
    witness = service.exact_witness(request)
    approximate_ids = {hit.chunk_id for hit in report.hits}
    exact_ids = {candidate.chunk_id for candidate in witness.candidates}
    artifact = VexExecutionArtifact(
        request={
            "generation_id": report.generation_id,
            "model_lock_artifact_id": "sha256:model-lock",
            "top_k": 3,
        },
        normalized_vector_sha256=witness.query_vector_sha256,
        plan={
            "algorithm": "hnsw",
            "backend": report.channel.value,
            "ef_search": 8,
        },
        candidates=tuple(
            VexCandidateRecord(report.channel.value, hit.rank, hit.score, hit.chunk_id)
            for hit in report.hits
        ),
        witness=witness,
        metrics={
            "recall_at_k": len(approximate_ids & exact_ids) / len(exact_ids),
            "result_reachability": 1.0,
        },
        decision=VexPolicyDecision(
            "bijux.canon.vex.policy_decision.v1",
            VexPolicyStatus.admitted,
            (),
        ),
        logs=("reachability verified",),
    )
    stored = VexArtifactStore(tmp_path / "artifacts").put(artifact)

    restarted_service = IndexService(
        service.registry_root,
        compatibility=compatibility,
    )
    restarted_store = VexArtifactStore(tmp_path / "artifacts")
    reloaded = restarted_store.load(stored.artifact_id)
    verified = restarted_service.verify()
    admitted_ids = Counter(chunk.chunk_id for chunk in _chunks())

    assert verified.generation_id == inspection.generation_id
    assert verified.integrity.status == "verified"
    _assert_reachable(
        dict(reloaded.record),
        admitted_ids=admitted_ids,
        generation_id=verified.generation_id,
        model_lock_artifact_id="sha256:model-lock",
    )
    assert restarted_store.load(stored.artifact_id) == reloaded


def test_reachability_oracle_rejects_missing_chunk_and_identity_drift() -> None:
    record: dict[str, object] = {
        "request": {
            "generation_id": "sha256:other",
            "model_lock_artifact_id": "sha256:model-lock",
        },
        "candidate_order": [{"chunk_id": "missing"}],
        "witness": {
            "generation_id": "sha256:generation",
            "model_lock_artifact_id": "sha256:model-lock",
            "candidates": [{"chunk_id": "missing"}],
        },
    }

    with pytest.raises(AssertionError):
        _assert_reachable(
            record,
            admitted_ids=Counter({"chunk-a": 1}),
            generation_id="sha256:generation",
            model_lock_artifact_id="sha256:model-lock",
        )
