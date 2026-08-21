# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("faiss")

from bijux_canon_index.application import (
    AdmittedIndexChunk,
    IndexBuildLimits,
    IndexCompatibility,
    IndexService,
    LexicalCandidateDisposition,
    LexicalCandidateOutcome,
    LexicalCandidateService,
)
from bijux_canon_index.domain.metadata_filters import MetadataFilter
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
            "Ancient DNA contamination constrains interpretation.",
            (0.0, 1.0, 0.0),
            {"source_id": "paper-b", "language": "sv"},
        ),
        AdmittedIndexChunk(
            "chunk-c",
            "paper-c",
            0,
            "DNA recovered from ancient remains.",
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


def test_lexical_candidates_retain_bm25_filter_and_limit_decisions(
    tmp_path: Path,
) -> None:
    root, generation_id, compatibility = _registry(tmp_path)
    service = LexicalCandidateService(root, compatibility=compatibility)

    batch = service.generate(
        "ancient dna",
        generation_id=generation_id,
        top_k=1,
        candidate_limit=3,
        metadata_filter=MetadataFilter(languages=("en",)),
    )

    assert batch.outcome is LexicalCandidateOutcome.success
    assert batch.generation_id == generation_id
    assert [decision.source_rank for decision in batch.decisions] == [1, 2]
    assert all(decision.score > 0 for decision in batch.decisions)
    assert [decision.output_rank for decision in batch.candidates] == [1]
    assert {decision.disposition for decision in batch.decisions} == {
        LexicalCandidateDisposition.included,
        LexicalCandidateDisposition.excluded_by_limit,
    }
    assert all(decision.chunk_id != "chunk-b" for decision in batch.decisions)
    assert all(len(decision.source_text_sha256) == 64 for decision in batch.decisions)

    restarted = LexicalCandidateService(root, compatibility=compatibility)
    assert (
        restarted.generate(
            "ancient dna",
            generation_id=generation_id,
            top_k=1,
            candidate_limit=3,
            metadata_filter=MetadataFilter(languages=("en",)),
        )
        == batch
    )


def test_lexical_candidates_handle_phrases_empty_and_filtered_empty(
    tmp_path: Path,
) -> None:
    root, generation_id, compatibility = _registry(tmp_path)
    service = LexicalCandidateService(root, compatibility=compatibility)

    phrase = service.generate(
        '"ancient DNA"',
        generation_id=generation_id,
        top_k=3,
        candidate_limit=3,
    )
    assert {candidate.chunk_id for candidate in phrase.candidates} == {
        "chunk-a",
        "chunk-b",
    }
    assert (
        service.generate(
            "   ",
            generation_id=generation_id,
            top_k=1,
            candidate_limit=1,
        ).outcome
        is LexicalCandidateOutcome.empty_query
    )
    assert (
        service.generate(
            "contamination",
            generation_id=generation_id,
            top_k=1,
            candidate_limit=1,
            metadata_filter=MetadataFilter(languages=("en",)),
        ).outcome
        is LexicalCandidateOutcome.filtered_empty
    )


def test_lexical_candidates_require_explicit_generation_and_bounded_pool(
    tmp_path: Path,
) -> None:
    root, generation_id, compatibility = _registry(tmp_path)
    service = LexicalCandidateService(root, compatibility=compatibility)

    with pytest.raises(ValueError, match="candidate_limit"):
        service.generate(
            "ancient",
            generation_id=generation_id,
            top_k=2,
            candidate_limit=1,
        )
    with pytest.raises(FileNotFoundError):
        service.generate(
            "ancient",
            generation_id="sha256:" + "f" * 64,
            top_k=1,
            candidate_limit=1,
        )


def test_lexical_filter_is_applied_before_candidate_limit(tmp_path: Path) -> None:
    root, generation_id, compatibility = _registry(tmp_path)
    service = LexicalCandidateService(root, compatibility=compatibility)

    batch = service.generate(
        "ancient dna",
        generation_id=generation_id,
        top_k=1,
        candidate_limit=1,
        metadata_filter=MetadataFilter(languages=("sv",)),
    )

    assert batch.outcome is LexicalCandidateOutcome.success
    assert [candidate.chunk_id for candidate in batch.candidates] == ["chunk-b"]
