# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

import pytest

pytest.importorskip("faiss")

from bijux_canon_index.application import (
    AdmittedIndexChunk,
    DenseCandidateCompatibilityError,
    DenseCandidateMode,
    DenseCandidateOutcome,
    DenseCandidateService,
    IndexBuildLimits,
    IndexCompatibility,
    IndexService,
    VexArtifactStore,
    VexExecutionBudget,
    VexPolicyStatus,
)
from bijux_canon_index.domain.metadata_filters import MetadataFilter
from bijux_canon_index.infra.adapters.faiss.hnsw import HnswParameters
from bijux_canon_index.infra.embeddings.local_model import EmbeddedBatch


class _LockedEmbedder:
    def __init__(
        self,
        vector: tuple[float, ...] = (1.0, 0.0, 0.0),
        *,
        model_lock_id: str = "sha256:model",
    ) -> None:
        self.vector = vector
        self.model_lock_id = model_lock_id
        self.calls: list[tuple[str, ...]] = []

    def embed(self, texts: Sequence[str]) -> EmbeddedBatch:
        self.calls.append(tuple(texts))
        return EmbeddedBatch((self.vector,), self.model_lock_id, "cpu", 1)


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
            "Contamination constrains interpretation.",
            (0.8, 0.2, 0.0),
            {"source_id": "paper-b", "language": "sv"},
        ),
        AdmittedIndexChunk(
            "chunk-c",
            "paper-c",
            0,
            "Population history from ancient remains.",
            (0.0, 0.0, 1.0),
            {"source_id": "paper-c", "language": "en"},
        ),
    )


def _registry(tmp_path: Path) -> tuple[Path, str, IndexCompatibility]:
    root = tmp_path / "registry"
    compatibility = IndexCompatibility("sha256:model", 3)
    report = IndexService(root, compatibility=compatibility).build(
        _chunks(),
        snapshot_artifact_id="sha256:snapshot",
        model_lock_artifact_id="sha256:model",
        limits=IndexBuildLimits(10, 10_000, 10_000, 10_000),
        hnsw_parameters=HnswParameters(m=2, ef_construction=8, ef_search=8, seed=17),
        activate=True,
    )
    return root, report.generation_id, compatibility


def _budget() -> VexExecutionBudget:
    return VexExecutionBudget(
        max_latency_ms=10_000,
        max_memory_bytes=100_000_000,
        max_candidates=10,
        max_ef_search=16,
        minimum_recall=0.5,
    )


@pytest.mark.parametrize("mode", tuple(DenseCandidateMode))
def test_dense_candidates_embed_once_and_persist_complete_vex_provenance(
    tmp_path: Path,
    mode: DenseCandidateMode,
) -> None:
    root, generation_id, compatibility = _registry(tmp_path)
    embedder = _LockedEmbedder()
    artifacts = tmp_path / "artifacts"
    service = DenseCandidateService(
        root,
        embedder=embedder,
        artifact_store_root=artifacts,
        compatibility=compatibility,
    )

    batch = service.generate(
        "ancient DNA",
        generation_id=generation_id,
        mode=mode,
        top_k=1,
        candidate_limit=2,
        budget=_budget(),
    )

    assert batch.outcome is DenseCandidateOutcome.success
    assert batch.decision.status is VexPolicyStatus.admitted
    assert batch.generation_id == generation_id
    assert batch.model_lock_artifact_id == "sha256:model"
    assert len(batch.candidates) == 2
    assert batch.candidates[0].chunk_id == "chunk-a"
    assert embedder.calls == [("ancient DNA",)]
    stored = VexArtifactStore(artifacts).load(batch.artifact_id)
    assert stored.record["execution_id"] == batch.execution_id
    assert stored.record["normalized_vector_sha256"] == batch.query_vector_sha256
    assert stored.record["witness"]["witness_id"] == batch.witness_id
    assert stored.record["request"]["candidate_limit"] == 2
    assert stored.record["request"]["query_text_sha256"] == batch.query_text_sha256
    assert stored.record["metrics"]["result_reachability"] == 1.0
    assert stored.record["plan"]["backend"] in {"faiss-flat-ip", "faiss-hnsw"}
    assert stored.record["plan"]["embedding_inference_threads"] == 1

    restarted = DenseCandidateService(
        root,
        embedder=_LockedEmbedder(),
        artifact_store_root=artifacts,
        compatibility=compatibility,
    ).generate(
        "ancient DNA",
        generation_id=generation_id,
        mode=mode,
        top_k=1,
        candidate_limit=2,
        budget=_budget(),
    )
    assert restarted.execution_id == batch.execution_id
    assert restarted.witness_id == batch.witness_id
    assert restarted.candidates == batch.candidates


def test_dense_candidates_retain_refused_attempt_without_exposing_results(
    tmp_path: Path,
) -> None:
    root, generation_id, compatibility = _registry(tmp_path)
    service = DenseCandidateService(
        root,
        embedder=_LockedEmbedder(),
        artifact_store_root=tmp_path / "artifacts",
        compatibility=compatibility,
    )

    batch = service.generate(
        "ancient DNA",
        generation_id=generation_id,
        mode=DenseCandidateMode.ann,
        top_k=1,
        candidate_limit=2,
        budget=replace(_budget(), max_ef_search=7),
    )

    assert batch.outcome is DenseCandidateOutcome.refused
    assert batch.decision.status is VexPolicyStatus.refused
    assert batch.candidates == ()
    assert len(batch.observed_candidates) == 2
    assert VexArtifactStore(tmp_path / "artifacts").load(batch.artifact_id)


def test_dense_candidates_persist_typed_filtered_empty_result(tmp_path: Path) -> None:
    root, generation_id, compatibility = _registry(tmp_path)
    artifacts = tmp_path / "artifacts"
    service = DenseCandidateService(
        root,
        embedder=_LockedEmbedder(),
        artifact_store_root=artifacts,
        compatibility=compatibility,
    )

    batch = service.generate(
        "ancient DNA",
        generation_id=generation_id,
        mode=DenseCandidateMode.exact,
        top_k=1,
        candidate_limit=2,
        budget=_budget(),
        metadata_filter=MetadataFilter(languages=("fr",)),
    )

    assert batch.outcome is DenseCandidateOutcome.no_matches
    assert batch.candidates == ()
    assert (
        VexArtifactStore(artifacts).load(batch.artifact_id).record["candidate_order"]
        == []
    )


@pytest.mark.parametrize(
    ("embedder", "message"),
    [
        (_LockedEmbedder(model_lock_id="sha256:other"), "model lock"),
        (_LockedEmbedder((1.0, 0.0)), "dimension"),
    ],
)
def test_dense_candidates_refuse_embedding_identity_drift_before_execution(
    tmp_path: Path,
    embedder: _LockedEmbedder,
    message: str,
) -> None:
    root, generation_id, compatibility = _registry(tmp_path)
    service = DenseCandidateService(
        root,
        embedder=embedder,
        artifact_store_root=tmp_path / "artifacts",
        compatibility=compatibility,
    )

    with pytest.raises(DenseCandidateCompatibilityError, match=message):
        service.generate(
            "ancient DNA",
            generation_id=generation_id,
            mode=DenseCandidateMode.exact,
            top_k=1,
            candidate_limit=1,
            budget=_budget(),
        )
    assert not list((tmp_path / "artifacts").rglob("*.json"))


def test_dense_candidate_bounds_are_validated_before_embedding(tmp_path: Path) -> None:
    root, generation_id, compatibility = _registry(tmp_path)
    embedder = _LockedEmbedder()
    service = DenseCandidateService(
        root,
        embedder=embedder,
        artifact_store_root=tmp_path / "artifacts",
        compatibility=compatibility,
    )

    with pytest.raises(ValueError, match="candidate_limit"):
        service.generate(
            "ancient DNA",
            generation_id=generation_id,
            mode=DenseCandidateMode.exact,
            top_k=2,
            candidate_limit=1,
            budget=_budget(),
        )
    assert embedder.calls == []
