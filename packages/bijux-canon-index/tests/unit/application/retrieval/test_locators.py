# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path

import pytest

pytest.importorskip("faiss")

from bijux_canon_index.application import (
    AdmittedIndexChunk,
    CitationCandidate,
    CitationChannel,
    CitationChannelProvenance,
    CitationLocatorCatalog,
    CitationLocatorRecord,
    CitationLocatorSegment,
    CitationLocatorService,
    CitationResolutionError,
    CitationResolutionErrorCode,
    CitationRetrievalMode,
    CitationSourceMetadata,
    DenseCandidate,
    DenseCandidateBatch,
    DenseCandidateMode,
    DenseCandidateOutcome,
    ExactSourceLocator,
    FusionChannelRanking,
    IndexBuildLimits,
    IndexCompatibility,
    IndexService,
    LexicalCandidateService,
    RankedChannelCandidate,
    RetrievalChannel,
    RrfFusionPolicy,
    VexPolicyDecision,
    VexPolicyStatus,
    citation_candidates_from_dense,
    citation_candidates_from_fusion,
    citation_candidates_from_lexical,
    reciprocal_rank_fusion,
)
from bijux_canon_index.infra.adapters.faiss.hnsw import HnswParameters

_SOURCE_SHA = "a" * 64
_QUERY_SHA = hashlib.sha256(b"ancient dna").hexdigest()


def _text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _registry(tmp_path: Path) -> tuple[Path, str, IndexCompatibility]:
    root = tmp_path / "registry"
    compatibility = IndexCompatibility("sha256:model", 3)
    report = IndexService(root, compatibility=compatibility).build(
        (
            AdmittedIndexChunk(
                "chunk-a",
                "paper-a",
                0,
                "Ancient DNA preserves direct evidence.",
                (1.0, 0.0, 0.0),
                {
                    "format": "jats",
                    "language": "en",
                    "source_id": "paper-a",
                    "source_sha256": _SOURCE_SHA,
                },
            ),
            AdmittedIndexChunk(
                "chunk-b",
                "paper-a",
                1,
                "Contamination constrains interpretation.",
                (0.0, 1.0, 0.0),
                {
                    "format": "jats",
                    "language": "en",
                    "source_id": "paper-a",
                    "source_sha256": _SOURCE_SHA,
                },
            ),
        ),
        snapshot_artifact_id="sha256:snapshot",
        model_lock_artifact_id="sha256:model",
        limits=IndexBuildLimits(10, 10_000, 10_000, 10_000),
        hnsw_parameters=HnswParameters(m=2, ef_construction=8, ef_search=8, seed=17),
        activate=True,
    )
    return root, report.generation_id, compatibility


def _source() -> CitationSourceMetadata:
    return CitationSourceMetadata(
        source_id="paper-a",
        source_uri="https://doi.org/10.0000/example",
        source_content_sha256=_SOURCE_SHA,
        format_id="jats",
        title="An ancient DNA paper",
        authors=("Researcher A",),
        doi="10.0000/example",
        language="en",
        license_id="CC-BY-4.0",
        journal="Journal of Ancient Evidence",
        publication_date="2026-08-24",
        license_url="https://creativecommons.org/licenses/by/4.0/",
        provenance_artifact_id="sha256:" + "9" * 64,
    )


def _record(
    chunk_id: str,
    ordinal: int,
    text: str,
) -> CitationLocatorRecord:
    start = ordinal * 1000
    return CitationLocatorRecord(
        chunk_id=chunk_id,
        document_id="paper-a",
        ordinal=ordinal,
        source=_source(),
        section_path=("article", "results"),
        locator=ExactSourceLocator(
            "jats-normalized-text-span",
            (
                ("char_start", start),
                ("char_end", start + len(text)),
                ("element_path", "/article[1]/body[1]/sec[1]"),
            ),
        ),
        verbatim_text=text,
        content_sha256=_text_sha256(text),
        mapping_ids=("sha256:" + f"{ordinal + 1:064x}",),
    )


def _catalog(*records: CitationLocatorRecord) -> CitationLocatorCatalog:
    return CitationLocatorCatalog(
        "bijux.canon.ingest.citation_locator_catalog.v1",
        "sha256:snapshot",
        records,
    )


def _candidate(
    *,
    channel: CitationChannel,
    chunk_id: str = "chunk-a",
    text: str = "Ancient DNA preserves direct evidence.",
) -> CitationCandidate:
    return CitationCandidate(
        rank=1,
        retrieval_rank=1,
        retrieval_score=0.75,
        rerank_score=None,
        chunk_id=chunk_id,
        document_id="paper-a",
        ordinal=0,
        source_text_sha256=_text_sha256(text),
        channels=(
            CitationChannelProvenance(
                channel,
                1,
                0.75,
                "sha256:" + "c" * 64,
            ),
        ),
    )


def test_lexical_hits_resolve_to_exact_source_text_and_lineage(tmp_path: Path) -> None:
    root, generation_id, compatibility = _registry(tmp_path)
    lexical = LexicalCandidateService(root, compatibility=compatibility).generate(
        "ancient dna",
        generation_id=generation_id,
        top_k=1,
        candidate_limit=2,
    )
    candidates = citation_candidates_from_lexical(lexical)
    record = _record("chunk-a", 0, "Ancient DNA preserves direct evidence.")

    batch = CitationLocatorService(root, compatibility=compatibility).resolve(
        candidates,
        generation_id=generation_id,
        query_text_sha256=lexical.query_text_sha256,
        retrieval_mode=CitationRetrievalMode.lexical,
        catalog=_catalog(record),
    )

    assert batch.snapshot_artifact_id == "sha256:snapshot"
    assert batch.locator_catalog_id.startswith("sha256:")
    assert len(batch.hits) == 1
    hit = batch.hits[0]
    assert hit.verbatim_text == record.verbatim_text
    assert hit.content_sha256 == _text_sha256(hit.verbatim_text)
    assert hit.source.source_content_sha256 == _SOURCE_SHA
    assert hit.source.authors == ("Researcher A",)
    assert hit.source.journal == "Journal of Ancient Evidence"
    assert hit.source.publication_date == "2026-08-24"
    assert hit.source.license_id == "CC-BY-4.0"
    assert hit.source.provenance_artifact_id == "sha256:" + "9" * 64
    assert hit.section_path == ("article", "results")
    assert dict(hit.locator.selectors)["char_start"] == 0
    assert hit.mapping_ids == record.mapping_ids
    assert hit.channels[0].channel is CitationChannel.lexical

    restarted = CitationLocatorService(root, compatibility=compatibility)
    assert (
        restarted.resolve(
            candidates,
            generation_id=generation_id,
            query_text_sha256=lexical.query_text_sha256,
            retrieval_mode=CitationRetrievalMode.lexical,
            catalog=_catalog(record),
        )
        == batch
    )


def test_multi_mapping_chunk_retains_each_exact_format_locator(tmp_path: Path) -> None:
    root, generation_id, compatibility = _registry(tmp_path)
    lexical = LexicalCandidateService(root, compatibility=compatibility).generate(
        "ancient dna",
        generation_id=generation_id,
        top_k=1,
        candidate_limit=2,
    )
    text = "Ancient DNA preserves direct evidence."
    first_text = "Ancient DNA"
    second_text = "preserves direct evidence."
    mapping_ids = ("sha256:" + "1" * 64, "sha256:" + "2" * 64)
    first_locator = ExactSourceLocator(
        "jats-element-path",
        (("element_path", "/article[1]/body[1]/p[1]"),),
    )
    second_locator = ExactSourceLocator(
        "jats-element-path",
        (("element_path", "/article[1]/body[1]/p[2]"),),
    )
    record = CitationLocatorRecord(
        chunk_id="chunk-a",
        document_id="paper-a",
        ordinal=0,
        source=_source(),
        section_path=("article", "results"),
        locator=first_locator,
        verbatim_text=text,
        content_sha256=_text_sha256(text),
        mapping_ids=mapping_ids,
        locator_segments=(
            CitationLocatorSegment(
                ordinal=0,
                mapping_id=mapping_ids[0],
                chunk_start=0,
                chunk_end=len(first_text),
                normalized_start=0,
                normalized_end=len(first_text),
                section_path=("article", "results"),
                locator=first_locator,
                verbatim_text=first_text,
                content_sha256=_text_sha256(first_text),
            ),
            CitationLocatorSegment(
                ordinal=1,
                mapping_id=mapping_ids[1],
                chunk_start=len(first_text) + 1,
                chunk_end=len(text),
                normalized_start=0,
                normalized_end=len(second_text),
                section_path=("article", "results"),
                locator=second_locator,
                verbatim_text=second_text,
                content_sha256=_text_sha256(second_text),
            ),
        ),
    )

    batch = CitationLocatorService(root, compatibility=compatibility).resolve(
        citation_candidates_from_lexical(lexical),
        generation_id=generation_id,
        query_text_sha256=lexical.query_text_sha256,
        retrieval_mode=CitationRetrievalMode.lexical,
        catalog=_catalog(record),
    )

    assert len(batch.hits[0].locator_segments) == 2
    assert batch.hits[0].locator_scope == "first-segment-only"
    assert [
        dict(segment.locator.selectors)["element_path"]
        for segment in batch.hits[0].locator_segments
    ] == ["/article[1]/body[1]/p[1]", "/article[1]/body[1]/p[2]"]


def test_dense_and_hybrid_modes_retain_exact_backend_provenance(
    tmp_path: Path,
) -> None:
    root, generation_id, compatibility = _registry(tmp_path)
    text = "Ancient DNA preserves direct evidence."
    text_sha256 = _text_sha256(text)
    dense = DenseCandidateBatch(
        schema_version="bijux.canon.retrieval.dense_candidates.v1",
        generation_id=generation_id,
        model_lock_artifact_id="sha256:model",
        query_text_sha256=_QUERY_SHA,
        query_vector_sha256="b" * 64,
        mode=DenseCandidateMode.exact,
        requested_top_k=1,
        candidate_limit=2,
        outcome=DenseCandidateOutcome.success,
        observed_candidates=(
            DenseCandidate(1, 0.9, "chunk-a", "paper-a", 0, text_sha256),
            DenseCandidate(
                2,
                0.8,
                "chunk-b",
                "paper-a",
                1,
                _text_sha256("Contamination constrains interpretation."),
            ),
        ),
        witness_id="sha256:" + "d" * 64,
        execution_id="sha256:" + "e" * 64,
        artifact_id="sha256:" + "f" * 64,
        decision=VexPolicyDecision(
            "bijux.canon.vex.policy_decision.v1",
            VexPolicyStatus.admitted,
            (),
        ),
    )
    service = CitationLocatorService(root, compatibility=compatibility)
    catalog = _catalog(_record("chunk-a", 0, text))

    dense_candidates = citation_candidates_from_dense(dense)
    assert len(dense_candidates) == dense.requested_top_k
    dense_result = service.resolve(
        dense_candidates,
        generation_id=generation_id,
        query_text_sha256=_QUERY_SHA,
        retrieval_mode=CitationRetrievalMode.dense_exact,
        catalog=catalog,
    )
    assert dense_result.hits[0].channels[0].channel is CitationChannel.dense_exact
    assert dense_result.hits[0].channels[0].execution_artifact_id == dense.artifact_id

    lexical_ranking = FusionChannelRanking(
        generation_id,
        _QUERY_SHA,
        RetrievalChannel.lexical,
        (RankedChannelCandidate(1, 4.0, "chunk-a", "paper-a", 0, text_sha256),),
    )
    dense_ranking = FusionChannelRanking(
        generation_id,
        _QUERY_SHA,
        RetrievalChannel.dense,
        (RankedChannelCandidate(1, 0.9, "chunk-a", "paper-a", 0, text_sha256),),
    )
    fusion = reciprocal_rank_fusion(
        (lexical_ranking, dense_ranking),
        policy=RrfFusionPolicy(top_k=1),
    )
    for mode, dense_mode, expected in (
        (
            CitationRetrievalMode.local_hybrid_exact,
            DenseCandidateMode.exact,
            {CitationChannel.lexical, CitationChannel.dense_exact},
        ),
        (
            CitationRetrievalMode.local_hybrid_ann,
            DenseCandidateMode.ann,
            {CitationChannel.lexical, CitationChannel.dense_ann},
        ),
    ):
        resolved = service.resolve(
            citation_candidates_from_fusion(fusion, dense_mode=dense_mode),
            generation_id=generation_id,
            query_text_sha256=_QUERY_SHA,
            retrieval_mode=mode,
            catalog=catalog,
        )
        assert {item.channel for item in resolved.hits[0].channels} == expected
        assert all(
            item.candidate_artifact_id.startswith("sha256:")
            for item in resolved.hits[0].channels
        )


def test_locator_resolution_refuses_missing_duplicate_and_stale_truth(
    tmp_path: Path,
) -> None:
    root, generation_id, compatibility = _registry(tmp_path)
    service = CitationLocatorService(root, compatibility=compatibility)
    candidate = _candidate(channel=CitationChannel.lexical)
    record = _record("chunk-a", 0, "Ancient DNA preserves direct evidence.")

    with pytest.raises(CitationResolutionError) as missing:
        service.resolve(
            (candidate,),
            generation_id=generation_id,
            query_text_sha256=_QUERY_SHA,
            retrieval_mode=CitationRetrievalMode.lexical,
            catalog=_catalog(
                _record("chunk-b", 1, "Contamination constrains interpretation.")
            ),
        )
    assert missing.value.code is CitationResolutionErrorCode.locator_missing

    with pytest.raises(CitationResolutionError) as duplicate:
        service.resolve(
            (candidate,),
            generation_id=generation_id,
            query_text_sha256=_QUERY_SHA,
            retrieval_mode=CitationRetrievalMode.lexical,
            catalog=_catalog(record, record),
        )
    assert duplicate.value.code is CitationResolutionErrorCode.locator_ambiguous

    stale_candidate = replace(candidate, source_text_sha256="0" * 64)
    with pytest.raises(CitationResolutionError) as stale:
        service.resolve(
            (stale_candidate,),
            generation_id=generation_id,
            query_text_sha256=_QUERY_SHA,
            retrieval_mode=CitationRetrievalMode.lexical,
            catalog=_catalog(record),
        )
    assert stale.value.code is CitationResolutionErrorCode.text_identity_mismatch


def test_locator_resolution_refuses_snapshot_source_and_channel_drift(
    tmp_path: Path,
) -> None:
    root, generation_id, compatibility = _registry(tmp_path)
    service = CitationLocatorService(root, compatibility=compatibility)
    candidate = _candidate(channel=CitationChannel.lexical)
    record = _record("chunk-a", 0, "Ancient DNA preserves direct evidence.")

    with pytest.raises(CitationResolutionError) as snapshot:
        service.resolve(
            (candidate,),
            generation_id=generation_id,
            query_text_sha256=_QUERY_SHA,
            retrieval_mode=CitationRetrievalMode.lexical,
            catalog=replace(_catalog(record), snapshot_artifact_id="other"),
        )
    assert snapshot.value.code is CitationResolutionErrorCode.generation_mismatch

    drifted_source = replace(
        record,
        source=replace(record.source, source_content_sha256="b" * 64),
    )
    with pytest.raises(CitationResolutionError) as source:
        service.resolve(
            (candidate,),
            generation_id=generation_id,
            query_text_sha256=_QUERY_SHA,
            retrieval_mode=CitationRetrievalMode.lexical,
            catalog=_catalog(drifted_source),
        )
    assert source.value.code is CitationResolutionErrorCode.source_identity_mismatch

    with pytest.raises(CitationResolutionError) as channel:
        service.resolve(
            (candidate,),
            generation_id=generation_id,
            query_text_sha256=_QUERY_SHA,
            retrieval_mode=CitationRetrievalMode.dense_exact,
            catalog=_catalog(record),
        )
    assert channel.value.code is CitationResolutionErrorCode.candidate_set_invalid


def test_locator_resolution_refuses_mixed_filter_or_authorization_lineage(
    tmp_path: Path,
) -> None:
    root, generation_id, compatibility = _registry(tmp_path)
    service = CitationLocatorService(root, compatibility=compatibility)
    first = _candidate(channel=CitationChannel.lexical)
    second = replace(
        _candidate(
            channel=CitationChannel.lexical,
            chunk_id="chunk-b",
            text="Contamination constrains interpretation.",
        ),
        rank=2,
        retrieval_rank=2,
        filter_sha256="b" * 64,
        authorization_scope_id="sha256:" + "c" * 64,
    )

    with pytest.raises(CitationResolutionError) as mixed_filter:
        service.resolve(
            (first, second),
            generation_id=generation_id,
            query_text_sha256=_QUERY_SHA,
            retrieval_mode=CitationRetrievalMode.lexical,
            catalog=_catalog(
                _record("chunk-a", 0, "Ancient DNA preserves direct evidence."),
                _record("chunk-b", 1, "Contamination constrains interpretation."),
            ),
        )

    assert mixed_filter.value.code is CitationResolutionErrorCode.candidate_set_invalid


def test_locator_values_validate_content_lineage_and_span_bounds() -> None:
    with pytest.raises(ValueError, match="content hash"):
        replace(
            _record("chunk-a", 0, "text"),
            content_sha256="0" * 64,
        )
    with pytest.raises(ValueError, match="mapping identities"):
        replace(_record("chunk-a", 0, "text"), mapping_ids=())
    with pytest.raises(ValueError, match="span"):
        ExactSourceLocator(
            "text-span",
            (("char_start", 2), ("char_end", 1)),
        )
