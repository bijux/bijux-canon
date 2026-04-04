# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Execution request preparation and dispatch helpers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
import uuid

from bijux_canon_index.contracts.tx import Tx
from bijux_canon_index.core.config import ExecutionConfig
from bijux_canon_index.core.contracts.execution_contract import ExecutionContract
from bijux_canon_index.core.errors import (
    BudgetExceededError,
    InvariantError,
    ValidationError,
)
from bijux_canon_index.core.runtime.vector_execution import RandomnessProfile
from bijux_canon_index.core.types import (
    ExecutionArtifact,
    ExecutionBudget,
    ExecutionRequest,
    NDSettings,
)
from bijux_canon_index.domain.non_determinism.execution_model import (
    NonDeterministicExecutionModel,
)
from bijux_canon_index.domain.requests.request_execution import (
    execute_request,
    start_execution_session,
)
from bijux_canon_index.interfaces.schemas.requests import ExecutionRequestPayload


@dataclass(frozen=True)
class NormalizedExecutionRequest:
    correlation_id: str
    run_id: str
    artifact: ExecutionArtifact
    randomness_profile: RandomnessProfile | None
    nd_model: NonDeterministicExecutionModel
    request: ExecutionRequest


def resolve_correlation_id(raw: str | None) -> str:
    return raw or "req-1"


def validate_execute_limits(
    config: ExecutionConfig, req: ExecutionRequestPayload
) -> None:
    if req.vector is None:
        raise ValidationError(message="execution vector required")
    limits = config.resource_limits
    if limits and limits.max_k is not None and req.top_k > int(limits.max_k):
        raise BudgetExceededError(message="top_k exceeds max_k limit")
    if (
        limits
        and limits.max_query_size is not None
        and req.request_text
        and len(req.request_text) > int(limits.max_query_size)
    ):
        raise BudgetExceededError(message="request_text exceeds max_query_size limit")


def resolve_execution_artifact(
    req: ExecutionRequestPayload,
    *,
    default_artifact_id: str,
    stores: Any,
    require_artifact: Callable[[str], ExecutionArtifact],
) -> ExecutionArtifact:
    artifact_id = req.artifact_id
    if artifact_id is None:
        available = tuple(stores.ledger.list_artifacts())
        if len(available) == 1:
            artifact_id = available[0].artifact_id
        else:
            raise ValidationError(message="artifact_id required for execution")
    artifact = require_artifact(artifact_id)
    if artifact.execution_contract is not req.execution_contract:
        raise InvariantError(
            message="Execution contract does not match artifact execution contract"
        )
    return artifact


def build_randomness_profile(
    req: ExecutionRequestPayload,
) -> RandomnessProfile | None:
    randomness_budget = None
    if req.execution_budget:
        randomness_budget = {
            key: value
            for key, value in {
                "max_latency_ms": req.execution_budget.max_latency_ms,
                "max_memory_mb": req.execution_budget.max_memory_mb,
                "max_error": req.execution_budget.max_error,
            }.items()
            if value is not None
        }
    if not req.randomness_profile:
        return None
    return RandomnessProfile(
        seed=req.randomness_profile.seed,
        sources=tuple(req.randomness_profile.sources or ()),
        bounded=req.randomness_profile.bounded,
        non_replayable=req.randomness_profile.non_replayable,
        budget=randomness_budget if randomness_budget else None,
        envelopes=tuple(
            (key, float(value))
            for key, value in (randomness_budget or {}).items()
            if isinstance(value, (int, float))
        ),
    )


def build_execution_request(
    req: ExecutionRequestPayload,
    correlation_id: str,
    nd_settings: NDSettings | None,
) -> ExecutionRequest:
    return ExecutionRequest(
        request_id=correlation_id,
        text=req.request_text,
        vector=tuple(req.vector or ()),
        top_k=req.top_k,
        execution_contract=req.execution_contract,
        execution_intent=req.execution_intent,
        execution_mode=req.execution_mode,
        execution_budget=ExecutionBudget(
            max_latency_ms=req.execution_budget.max_latency_ms
            if req.execution_budget
            else None,
            max_memory_mb=req.execution_budget.max_memory_mb
            if req.execution_budget
            else None,
            max_error=req.execution_budget.max_error if req.execution_budget else None,
        ),
        nd_settings=nd_settings,
    )


def normalize_execute_request(
    req: ExecutionRequestPayload,
    *,
    config: ExecutionConfig,
    stores: Any,
    default_artifact_id: str,
    require_artifact: Callable[[str], ExecutionArtifact],
    latest_vector_fingerprint: str | None,
    tx_factory: Callable[[], Tx],
    ann_runner: Any,
) -> NormalizedExecutionRequest:
    validate_execute_limits(config, req)
    correlation_id = resolve_correlation_id(req.correlation_id)
    artifact = resolve_execution_artifact(
        req,
        default_artifact_id=default_artifact_id,
        stores=stores,
        require_artifact=require_artifact,
    )
    randomness_profile = build_randomness_profile(req)
    nd_model = NonDeterministicExecutionModel(
        stores=stores,
        ann_runner=ann_runner,
        latest_vector_fingerprint=latest_vector_fingerprint,
        tx_factory=tx_factory,
    )
    nd_settings = nd_model.build_settings(req)
    request = build_execution_request(req, correlation_id, nd_settings)
    return NormalizedExecutionRequest(
        correlation_id=correlation_id,
        run_id=f"{correlation_id}-{uuid.uuid4().hex}",
        artifact=artifact,
        randomness_profile=randomness_profile,
        nd_model=nd_model,
        request=request,
    )


def dispatch_execution(
    req: ExecutionRequestPayload,
    *,
    artifact: ExecutionArtifact,
    request: ExecutionRequest,
    randomness_profile: RandomnessProfile | None,
    nd_model: NonDeterministicExecutionModel,
    stores: Any,
    ann_runner: Any,
) -> tuple[Any, Any]:
    if req.execution_contract is ExecutionContract.NON_DETERMINISTIC:
        return nd_model.execute(
            artifact,
            request,
            randomness_profile,
            build_on_demand=req.nd_build_on_demand,
        )
    session = start_execution_session(
        artifact,
        request,
        stores,
        randomness=randomness_profile,
        ann_runner=ann_runner,
    )
    return execute_request(session, stores, ann_runner=ann_runner)


__all__ = [
    "NormalizedExecutionRequest",
    "build_execution_request",
    "build_randomness_profile",
    "dispatch_execution",
    "normalize_execute_request",
    "resolve_correlation_id",
    "resolve_execution_artifact",
    "validate_execute_limits",
]
