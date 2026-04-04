# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from dataclasses import replace
import json
from typing import Any

from bijux_canon_index.core.contracts.execution_contract import ExecutionContract
from bijux_canon_index.core.execution_intent import ExecutionIntent
from bijux_canon_index.core.execution_mode import ExecutionMode
from bijux_canon_index.core.runtime.execution_plan import ExecutionPlan
from bijux_canon_index.core.runtime.vector_execution import (
    derive_execution_id,
    execution_signature,
)
from bijux_canon_index.core.types import (
    ExecutionArtifact,
    ExecutionBudget,
    ExecutionRequest,
)
from bijux_canon_index.interfaces.schemas.requests import ExecutionArtifactRequest


def build_materialized_artifact(
    *,
    artifact_id: str,
    request: ExecutionArtifactRequest,
    corpus_fingerprint: str,
    vector_fingerprint: str,
    build_params: tuple[tuple[str, str], ...],
    backend_name: str,
) -> ExecutionArtifact:
    artifact = ExecutionArtifact(
        artifact_id=artifact_id,
        corpus_fingerprint=corpus_fingerprint,
        vector_fingerprint=vector_fingerprint,
        metric="l2",
        scoring_version="v1",
        schema_version="v1",
        execution_contract=request.execution_contract,
        build_params=build_params,
        index_state="unbuilt"
        if request.execution_contract is ExecutionContract.NON_DETERMINISTIC
        else "ready",
    )
    plan = ExecutionPlan(
        algorithm="exact_vector_execution",
        contract=request.execution_contract,
        k=0,
        scoring_fn=artifact.metric,
        randomness_sources=(),
        reproducibility_bounds="bit-identical",
    )
    execution_id = derive_execution_id(
        request=ExecutionRequest(
            request_id="materialize",
            text=None,
            vector=None,
            top_k=0,
            execution_contract=request.execution_contract,
            execution_intent=ExecutionIntent.EXACT_VALIDATION,
            execution_mode=(
                ExecutionMode.STRICT
                if request.execution_contract is ExecutionContract.DETERMINISTIC
                else ExecutionMode.BOUNDED
            ),
            execution_budget=(
                ExecutionBudget()
                if request.execution_contract is ExecutionContract.NON_DETERMINISTIC
                else None
            ),
        ),
        backend_id=backend_name,
        algorithm="exact_vector_execution",
        plan=plan,
    )
    return replace(
        artifact,
        execution_plan=plan,
        execution_signature=execution_signature(
            plan, artifact.corpus_fingerprint, artifact.vector_fingerprint, None
        ),
        execution_id=execution_id,
    )


def attach_ann_index(
    *,
    artifact: ExecutionArtifact,
    ann_runner: Any,
    vectors: list[Any],
) -> ExecutionArtifact:
    index_info = ann_runner.build_index(
        artifact.artifact_id, vectors, artifact.metric, None
    )
    if not index_info:
        return artifact
    index_hash = index_info.get("index_hash")
    extra: tuple[tuple[str, str], ...] = (
        ("ann_index_info", json.dumps(index_info, sort_keys=True)),
    )
    if index_hash:
        extra = extra + (("ann_index_hash", str(index_hash)),)
    return replace(
        artifact,
        build_params=artifact.build_params + extra,
        index_state="ready",
    )


def materialization_response(artifact: ExecutionArtifact) -> dict[str, object]:
    return {
        "artifact_id": artifact.artifact_id,
        "execution_contract": artifact.execution_contract.value,
        "execution_contract_status": (
            "stable"
            if artifact.execution_contract is ExecutionContract.DETERMINISTIC
            else "experimental"
        ),
        "replayable": artifact.replayable,
    }


__all__ = [
    "attach_ann_index",
    "build_materialized_artifact",
    "materialization_response",
]
