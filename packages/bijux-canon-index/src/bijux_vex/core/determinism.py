# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from dataclasses import dataclass

from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.errors import (
    BackendCapabilityError,
    DeterminismViolationError,
    NDExecutionUnavailableError,
)
from bijux_vex.core.runtime.vector_execution import RandomnessProfile
from bijux_vex.infra.adapters.ann_base import AnnExecutionRequestRunner
from bijux_vex.infra.adapters.vectorstore_registry import VectorStoreDescriptor
from bijux_vex.infra.logging import log_event


@dataclass(frozen=True)
class DeterminismClassification:
    label: str
    randomness_sources: tuple[str, ...]
    reasons: tuple[str, ...]


def classify_execution(
    *,
    contract: ExecutionContract,
    randomness: RandomnessProfile | None,
    ann_runner: AnnExecutionRequestRunner | None,
    vector_store: VectorStoreDescriptor | None,
    require_randomness: bool = True,
) -> DeterminismClassification:
    if contract is ExecutionContract.DETERMINISTIC:
        if randomness is not None:
            raise DeterminismViolationError(
                message="Deterministic execution forbids randomness profiles"
            )
        if vector_store and not vector_store.deterministic_exact:
            raise DeterminismViolationError(
                message="Deterministic execution requires a deterministic vector store"
            )
        classification = DeterminismClassification(
            label="deterministic", randomness_sources=(), reasons=()
        )
        log_event(
            "determinism_classification",
            contract=contract.value,
            vector_store=vector_store.name if vector_store else None,
            label=classification.label,
            randomness_sources=",".join(classification.randomness_sources),
        )
        return classification

    # Non-deterministic / ANN path
    if vector_store and not vector_store.supports_ann:
        raise BackendCapabilityError(
            message="Approximate execution requested but vector store does not support ANN"
        )
    if ann_runner is None and not (vector_store and vector_store.supports_ann):
        raise NDExecutionUnavailableError(
            message="Non-deterministic execution requested without ANN support"
        )
    if randomness is None and require_randomness:
        raise DeterminismViolationError(
            message="Non-deterministic execution requires declared randomness"
        )
    if randomness is None:
        classification = DeterminismClassification(
            label="nondeterministic", randomness_sources=(), reasons=()
        )
        log_event(
            "determinism_classification",
            contract=contract.value,
            vector_store=vector_store.name if vector_store else None,
            label=classification.label,
            randomness_sources=",".join(classification.randomness_sources),
        )
        return classification
    if ann_runner is not None and ann_runner.supports_seed:
        if randomness.seed is None:
            raise DeterminismViolationError(
                message="Non-deterministic execution requires seed for replayable ANN"
            )
    else:
        if randomness.seed is None and (
            not randomness.sources or not randomness.non_replayable
        ):
            raise DeterminismViolationError(
                message="Non-deterministic execution requires seed or "
                "non_replayable randomness sources"
            )
    label = "bounded" if randomness.bounded else "nondeterministic"
    classification = DeterminismClassification(
        label=label,
        randomness_sources=tuple(randomness.sources),
        reasons=(),
    )
    log_event(
        "determinism_classification",
        contract=contract.value,
        vector_store=vector_store.name if vector_store else None,
        label=classification.label,
        randomness_sources=",".join(classification.randomness_sources),
    )
    return classification


__all__ = ["DeterminismClassification", "classify_execution"]
