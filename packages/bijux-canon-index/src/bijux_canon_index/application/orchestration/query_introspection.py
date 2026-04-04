# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from bijux_canon_index.core.contracts.execution_contract import ExecutionContract
from bijux_canon_index.core.errors import (
    InvariantError,
    NotFoundError,
    ReplayNotSupportedError,
    ValidationError,
)
from bijux_canon_index.core.execution_intent import ExecutionIntent
from bijux_canon_index.core.execution_mode import ExecutionMode
from bijux_canon_index.core.runtime.vector_execution import RandomnessProfile
from bijux_canon_index.core.types import (
    Chunk,
    Document,
    ExecutionArtifact,
    ExecutionBudget,
    ExecutionRequest,
    Vector,
)
from bijux_canon_index.domain.provenance.lineage import explain_result
from bijux_canon_index.domain.provenance.replay import replay
from bijux_canon_index.domain.requests.execution_diff import compare_executions
from bijux_canon_index.domain.requests.request_execution import (
    execute_request,
    start_execution_session,
)
from bijux_canon_index.interfaces.schemas.requests import (
    ExecutionRequestPayload,
    ExplainRequest,
)


def build_explain_response(
    req: ExplainRequest,
    *,
    stores: Any,
    require_artifact: Callable[[str], ExecutionArtifact],
) -> dict[str, Any]:
    art_id = req.artifact_id
    if art_id is None:
        artifacts = tuple(stores.ledger.list_artifacts())
        if len(artifacts) == 1:
            art_id = artifacts[0].artifact_id
        else:
            raise ValidationError(message="artifact_id required to explain result")
    artifact = require_artifact(art_id)
    latest = stores.ledger.latest_execution_result(artifact.artifact_id)
    if latest is None:
        raise NotFoundError(message="No execution results available to explain")
    target = next((r for r in latest.results if r.vector_id == req.result_id), None)
    if target is None:
        raise NotFoundError(message="result not found")
    data = explain_result(target, stores)
    document = cast(Document, data["document"])
    chunk = cast(Chunk, data["chunk"])
    vector = cast(Vector, data["vector"])
    artifact_meta = cast(ExecutionArtifact, data["artifact"])
    return {
        "document_id": document.document_id,
        "chunk_id": chunk.chunk_id,
        "vector_id": vector.vector_id,
        "artifact_id": artifact_meta.artifact_id,
        "metric": artifact_meta.metric,
        "score": target.score,
        "correlation_id": target.request_id,
        "execution_contract": artifact_meta.execution_contract.value,
        "execution_contract_status": (
            "stable"
            if artifact_meta.execution_contract is ExecutionContract.DETERMINISTIC
            else "experimental"
        ),
        "replayable": artifact_meta.replayable,
        "execution_id": latest.execution_id,
    }


def build_replay_response(
    request_text: str,
    *,
    expected_contract: ExecutionContract | None,
    artifact_id: str | None,
    randomness_profile: RandomnessProfile | None,
    execution_budget: ExecutionBudget | None,
    stores: Any,
    ann_runner: Any,
    require_artifact: Callable[[str], ExecutionArtifact],
) -> dict[str, Any]:
    chosen_artifact_id = artifact_id
    if chosen_artifact_id is None:
        artifacts = tuple(stores.ledger.list_artifacts())
        if len(artifacts) == 1:
            chosen_artifact_id = artifacts[0].artifact_id
        else:
            raise ValidationError(message="artifact_id required for replay")
    artifact = require_artifact(chosen_artifact_id)
    if expected_contract and expected_contract is not artifact.execution_contract:
        raise InvariantError(
            message="Replay contract does not match artifact execution contract"
        )
    if (
        artifact.execution_contract is ExecutionContract.NON_DETERMINISTIC
        and randomness_profile is None
    ):
        raise ReplayNotSupportedError(
            message="Non-deterministic replay requires explicit randomness profile"
        )
    if (
        artifact.execution_contract is ExecutionContract.NON_DETERMINISTIC
        and randomness_profile is not None
        and randomness_profile.non_replayable
    ):
        raise ReplayNotSupportedError(
            message="Non-deterministic replay refused for non-replayable requests"
        )
    if (
        artifact.execution_contract is ExecutionContract.NON_DETERMINISTIC
        and randomness_profile is not None
        and randomness_profile.seed is None
    ):
        raise ReplayNotSupportedError(
            message="Non-deterministic replay requires a seed"
        )
    request = ExecutionRequest(
        request_id="req-replay",
        text=request_text,
        vector=(0.0, 0.0),
        top_k=5,
        execution_contract=artifact.execution_contract,
        execution_intent=ExecutionIntent.REPRODUCIBLE_RESEARCH,
        execution_mode=ExecutionMode.STRICT
        if artifact.execution_contract is ExecutionContract.DETERMINISTIC
        else ExecutionMode.BOUNDED,
        execution_budget=execution_budget,
    )
    outcome = replay(
        request,
        artifact,
        stores,
        ann_runner=ann_runner,
        randomness=randomness_profile,
    )
    return {
        "matches": outcome.matches,
        "original_fingerprint": outcome.original_fingerprint,
        "replay_fingerprint": outcome.replay_fingerprint,
        "details": outcome.details,
        "nondeterministic_sources": outcome.nondeterministic_sources,
        "execution_contract": artifact.execution_contract.value,
        "execution_contract_status": (
            "stable"
            if artifact.execution_contract is ExecutionContract.DETERMINISTIC
            else "experimental"
        ),
        "replayable": artifact.replayable,
        "execution_id": outcome.execution_id,
    }


def build_compare_response(
    req: ExecutionRequestPayload,
    *,
    artifact_a_id: str | None,
    artifact_b_id: str | None,
    default_artifact_id: str,
    stores: Any,
    ann_runner: Any,
    require_artifact: Callable[[str], ExecutionArtifact],
) -> dict[str, object]:
    if req.vector is None:
        raise ValidationError(message="execution vector required for comparison")
    art_a = require_artifact(artifact_a_id or default_artifact_id)
    art_b = require_artifact(artifact_b_id or default_artifact_id)
    vector_values = tuple(req.vector)

    def as_request(artifact: ExecutionArtifact) -> ExecutionRequest:
        return ExecutionRequest(
            request_id=f"compare-{artifact.artifact_id}",
            text=req.request_text,
            vector=vector_values,
            top_k=req.top_k,
            execution_contract=artifact.execution_contract,
            execution_intent=req.execution_intent,
            execution_mode=req.execution_mode,
            execution_budget=ExecutionBudget(
                max_latency_ms=req.execution_budget.max_latency_ms
                if req.execution_budget
                else None,
                max_memory_mb=req.execution_budget.max_memory_mb
                if req.execution_budget
                else None,
                max_error=req.execution_budget.max_error
                if req.execution_budget
                else None,
            ),
        )

    session_a = start_execution_session(
        art_a, as_request(art_a), stores, ann_runner=ann_runner
    )
    session_b = start_execution_session(
        art_b, as_request(art_b), stores, ann_runner=ann_runner
    )
    exec_a, res_a = execute_request(session_a, stores, ann_runner=ann_runner)
    exec_b, res_b = execute_request(session_b, stores, ann_runner=ann_runner)
    diff = compare_executions(exec_a, res_a, exec_b, res_b)
    return {
        "execution_a": diff.execution_a.execution_id,
        "execution_b": diff.execution_b.execution_id,
        "overlap_ratio": diff.overlap_ratio,
        "recall_delta": diff.recall_delta,
        "rank_instability": diff.rank_instability,
        "execution_a_contract": art_a.execution_contract.value,
        "execution_b_contract": art_b.execution_contract.value,
        "execution_a_contract_status": (
            "stable"
            if art_a.execution_contract is ExecutionContract.DETERMINISTIC
            else "experimental"
        ),
        "execution_b_contract_status": (
            "stable"
            if art_b.execution_contract is ExecutionContract.DETERMINISTIC
            else "experimental"
        ),
    }


__all__ = [
    "build_compare_response",
    "build_explain_response",
    "build_replay_response",
]
