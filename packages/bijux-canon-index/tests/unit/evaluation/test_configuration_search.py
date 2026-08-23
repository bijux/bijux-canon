# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import pytest

from bijux_canon_index.evaluation import (
    ObservedLocatorSegment,
    ObservedFinalizationConfiguration,
    ObservedRetrievalHit,
    ObservedStageCandidate,
    PublicRetrievalEvaluationRequest,
    PublicRetrievalMode,
    RetrievalConfigurationSearchError,
    RetrievalExecutionObservation,
    RetrievalExecutionStatus,
    RetrievalSearchConfiguration,
    RetrievalStage,
    RetrievalStageEvidence,
    ReviewedRetrievalQrel,
    ReviewedRetrievalQuery,
    default_retrieval_search_configurations,
    observed_finalization_search_configuration,
    search_retrieval_configurations,
)


def _query() -> ReviewedRetrievalQuery:
    return ReviewedRetrievalQuery(
        query_id="question",
        query_text="Which content supports the claim?",
        input_identity_sha256="1" * 64,
        qrels=(ReviewedRetrievalQrel("qrel", "relevant", 3, "supports", "2" * 64),),
    )


def _request() -> PublicRetrievalEvaluationRequest:
    return PublicRetrievalEvaluationRequest.create(
        index_artifact_id=f"sha256:{'3' * 64}",
        split="development",
        mode=PublicRetrievalMode.hybrid_exact,
        queries=(_query(),),
    )


def _candidate(
    stage: RetrievalStage,
    chunk_id: str,
    rank: int,
) -> ObservedStageCandidate:
    return ObservedStageCandidate(stage, chunk_id, rank, rank, 1.0 / rank, "included")


def _observation(*, status: RetrievalExecutionStatus = RetrievalExecutionStatus.success) -> RetrievalExecutionObservation:
    failed = status in {RetrievalExecutionStatus.failed, RetrievalExecutionStatus.refused}
    return RetrievalExecutionObservation(
        query_id="question",
        query_text_sha256="a" * 64,
        status=status,
        generation_id=f"sha256:{'4' * 64}",
        model_lock_artifact_id=f"sha256:{'5' * 64}",
        configuration_id=f"sha256:{'6' * 64}",
        retrieval_mode="local-hybrid-exact",
        hits=() if failed else (
            ObservedRetrievalHit(
                1,
                1,
                1.0,
                "irrelevant",
                "document",
                "7" * 64,
                "8" * 64,
                (ObservedLocatorSegment(0, "mapping", "page", (("page", 1),), "8" * 64),),
            ),
        ),
        run_id=None if failed else "run",
        attempt_id=None if failed else "attempt",
        vex_artifact_id=None,
        policy_action="fail" if failed else "admit",
        fallback_action="none",
        stages=None if failed else RetrievalStageEvidence(
            lexical_outcome="success",
            dense_outcome="success",
            fusion_policy_sha256="9" * 64,
            rerank_policy_sha256="8" * 64,
            lexical_candidates=tuple(
                _candidate(RetrievalStage.lexical, chunk_id, rank)
                for rank, chunk_id in enumerate(("irrelevant", "relevant"), 1)
            ),
            dense_candidates=tuple(
                _candidate(RetrievalStage.dense, chunk_id, rank)
                for rank, chunk_id in enumerate(("relevant", "irrelevant"), 1)
            ),
            fusion_candidates=tuple(
                _candidate(RetrievalStage.fusion, chunk_id, rank)
                for rank, chunk_id in enumerate(("irrelevant", "relevant"), 1)
            ),
            rerank_candidates=tuple(
                _candidate(RetrievalStage.rerank, chunk_id, rank)
                for rank, chunk_id in enumerate(("relevant", "irrelevant"), 1)
            ),
        ),
        failure="execution failed" if failed else None,
    )


def _configuration() -> RetrievalSearchConfiguration:
    return RetrievalSearchConfiguration(10, 10, 10, 1, 1.0, 2.0)


def test_configuration_search_reranks_raw_channels_and_selects_first_pass() -> None:
    report = search_retrieval_configurations(
        request=_request(),
        observations=(_observation(),),
        configurations=(_configuration(),),
    )

    assert report.query_count == 1
    assert report.qrel_count == 1
    assert report.results[0].meets_floor is True
    assert report.selected_configuration_id == _configuration().configuration_id
    assert report.results[0].metrics.queries[0].reciprocal_rank_at_10 == 1.0


def test_configuration_search_can_select_observed_installed_finalization() -> None:
    observation = _observation()
    configuration = observed_finalization_search_configuration((observation,))

    report = search_retrieval_configurations(
        request=_request(),
        observations=(observation,),
        configurations=(configuration, _configuration()),
    )

    assert isinstance(configuration, ObservedFinalizationConfiguration)
    assert configuration.policy_sha256 == "8" * 64
    assert report.selected_configuration_id == configuration.configuration_id
    assert report.results[0].metrics.queries[0].reciprocal_rank_at_10 == 1.0


def test_configuration_search_keeps_execution_failures_in_denominator() -> None:
    report = search_retrieval_configurations(
        request=_request(),
        observations=(_observation(status=RetrievalExecutionStatus.refused),),
        configurations=(_configuration(),),
    )

    assert report.selected_configuration_id is None
    assert report.results[0].failed_metrics == (
        "recall-at-5",
        "mrr-at-10",
        "ndcg-at-10",
    )


def test_configuration_search_rejects_non_development_truth() -> None:
    heldout = PublicRetrievalEvaluationRequest.create(
        index_artifact_id=f"sha256:{'3' * 64}",
        split="heldout",
        mode=PublicRetrievalMode.hybrid_exact,
        queries=(_query(),),
    )

    with pytest.raises(RetrievalConfigurationSearchError, match="development truth"):
        search_retrieval_configurations(
            request=heldout,
            observations=(_observation(),),
            configurations=(_configuration(),),
        )


def test_configuration_identity_contains_only_general_ranking_parameters() -> None:
    fields = set(RetrievalSearchConfiguration.__dataclass_fields__)

    assert fields == {
        "candidate_depth",
        "dense_admission_limit",
        "dense_weight",
        "lexical_admission_limit",
        "lexical_weight",
        "rank_constant",
        "top_k",
    }
    assert not {"query_id", "document_id", "source_id"} & fields


def test_default_search_space_is_ordered_bounded_and_identity_free() -> None:
    configurations = default_retrieval_search_configurations(
        observed_candidate_depth=500
    )

    assert configurations
    assert configurations[0].candidate_depth == 40
    assert configurations[-1].candidate_depth == 500
    assert len({item.configuration_id for item in configurations}) == len(
        configurations
    )
    assert all(item.dense_admission_limit <= 500 for item in configurations)
