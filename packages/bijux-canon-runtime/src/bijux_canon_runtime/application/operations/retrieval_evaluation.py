# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Application-owned orchestration for reviewed retrieval evaluation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

from bijux_canon_index.evaluation import (
    ObservedFinalizationConfiguration,
    PublicRetrievalEvaluationReport,
    PublicRetrievalEvaluationRequest,
    PublicRetrievalMode,
    RetrievalConfigurationSearchReport,
    RetrievalSearchConfiguration,
    default_retrieval_search_configurations,
    load_reviewed_retrieval_request,
    observed_finalization_search_configuration,
    search_retrieval_configurations,
)

RuntimeRetrievalEvaluationReport: TypeAlias = PublicRetrievalEvaluationReport
RuntimeRetrievalConfigurationSearchReport: TypeAlias = (
    RetrievalConfigurationSearchReport
)
RuntimeRetrievalConfiguration: TypeAlias = (
    RetrievalSearchConfiguration | ObservedFinalizationConfiguration
)
RetrievalEvaluationExecutor: TypeAlias = Callable[
    [PublicRetrievalEvaluationRequest], PublicRetrievalEvaluationReport
]


@dataclass(frozen=True, slots=True)
class RuntimeRetrievalEvaluationInput:
    """Transport-neutral authority for one truth-only installed evaluation."""

    cases_path: Path
    qrels_path: Path
    index_artifact_id: str
    split: str = "development"
    mode: str = "local-hybrid-ann"
    top_k: int = 10

    def __post_init__(self) -> None:
        if not self.cases_path.is_absolute() or not self.qrels_path.is_absolute():
            raise ValueError("retrieval evaluation truth paths must be absolute")
        if not self.index_artifact_id.strip() or not self.split.strip():
            raise ValueError("retrieval evaluation identities must not be empty")
        PublicRetrievalMode(self.mode)
        if not 10 <= self.top_k <= 1000:
            raise ValueError("retrieval evaluation top_k must be within 10..1000")


def evaluate_reviewed_retrieval(
    parameters: RuntimeRetrievalEvaluationInput,
    *,
    execute: RetrievalEvaluationExecutor,
) -> RuntimeRetrievalEvaluationReport:
    """Load reviewed truth and execute every query through the installed owner."""
    request = _request(parameters)
    return execute(request)


def search_reviewed_retrieval_configurations(
    parameters: RuntimeRetrievalEvaluationInput,
    *,
    execute: RetrievalEvaluationExecutor,
) -> RuntimeRetrievalConfigurationSearchReport:
    """Search general configurations over one complete development observation set."""
    request = _request(parameters)
    evaluation = execute(request)
    observed_depth = max(
        parameters.top_k,
        max(
            (
                max(
                    len(observation.stages.lexical_candidates),
                    len(observation.stages.dense_candidates),
                )
                for observation in evaluation.observations
                if observation.stages is not None
            ),
            default=parameters.top_k,
        ),
    )
    return search_retrieval_configurations(
        request=request,
        observations=evaluation.observations,
        configurations=(
            observed_finalization_search_configuration(
                evaluation.observations,
                top_k=parameters.top_k,
            ),
            *default_retrieval_search_configurations(
                observed_candidate_depth=observed_depth,
                top_k=parameters.top_k,
            ),
        ),
    )


def retrieval_configuration_summary(
    configuration: RuntimeRetrievalConfiguration,
) -> str:
    """Describe one evaluated configuration without leaking owner types to transports."""
    if isinstance(configuration, ObservedFinalizationConfiguration):
        return (
            f"strategy={configuration.ranking_strategy}, "
            f"policy={configuration.policy_sha256}, top_k={configuration.top_k}"
        )
    return (
        f"strategy=weighted-rrf, depth={configuration.candidate_depth}, "
        f"lexical={configuration.lexical_admission_limit}, "
        f"dense={configuration.dense_admission_limit}, "
        f"k={configuration.rank_constant}, "
        f"weights={configuration.lexical_weight}:{configuration.dense_weight}"
    )


def _request(
    parameters: RuntimeRetrievalEvaluationInput,
) -> PublicRetrievalEvaluationRequest:
    return load_reviewed_retrieval_request(
        cases_path=parameters.cases_path,
        qrels_path=parameters.qrels_path,
        index_artifact_id=parameters.index_artifact_id,
        split=parameters.split,
        mode=PublicRetrievalMode(parameters.mode),
        top_k=parameters.top_k,
    )


__all__ = [
    "RetrievalEvaluationExecutor",
    "RuntimeRetrievalConfiguration",
    "RuntimeRetrievalConfigurationSearchReport",
    "RuntimeRetrievalEvaluationInput",
    "RuntimeRetrievalEvaluationReport",
    "evaluate_reviewed_retrieval",
    "retrieval_configuration_summary",
    "search_reviewed_retrieval_configurations",
]
