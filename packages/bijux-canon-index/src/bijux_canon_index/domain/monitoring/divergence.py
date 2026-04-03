# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Divergence detection across backends."""

from __future__ import annotations

from bijux_canon_index.contracts.resources import ExecutionResources
from bijux_canon_index.core.contracts.execution_contract import ExecutionContract
from bijux_canon_index.core.errors import BackendDivergenceError
from bijux_canon_index.core.types import ExecutionRequest
from bijux_canon_index.domain.requests.execution_diff import compare_executions
from bijux_canon_index.domain.requests.execute import (
    execute_request,
    start_execution_session,
)
from bijux_canon_index.infra.adapters.ann_base import AnnExecutionRequestRunner


def detect_backend_drift(
    artifact_id: str,
    request: ExecutionRequest,
    resources_a: ExecutionResources,
    resources_b: ExecutionResources,
    ann_runner_a: AnnExecutionRequestRunner | None = None,
    ann_runner_b: AnnExecutionRequestRunner | None = None,
    recall_floor: float = 0.5,
) -> None:
    artifact_a = resources_a.ledger.get_artifact(artifact_id)
    artifact_b = resources_b.ledger.get_artifact(artifact_id)
    if artifact_a is None or artifact_b is None:
        raise BackendDivergenceError(message="Missing artifacts for drift detection")
    session_a = start_execution_session(
        artifact_a, request, resources_a, ann_runner=ann_runner_a
    )
    session_b = start_execution_session(
        artifact_b, request, resources_b, ann_runner=ann_runner_b
    )
    exec_a, res_a = execute_request(session_a, resources_a, ann_runner=ann_runner_a)
    exec_b, res_b = execute_request(session_b, resources_b, ann_runner=ann_runner_b)
    diff = compare_executions(exec_a, res_a, exec_b, res_b)
    if request.execution_contract is ExecutionContract.DETERMINISTIC:
        if diff.overlap_ratio < 1.0:
            raise BackendDivergenceError(message="Deterministic backends diverged")
    else:
        if diff.overlap_ratio < recall_floor:
            raise BackendDivergenceError(message="Approximate backends drifted")


__all__ = ["detect_backend_drift"]
