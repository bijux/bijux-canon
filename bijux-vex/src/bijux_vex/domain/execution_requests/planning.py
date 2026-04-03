# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

import secrets

from bijux_vex.contracts.resources import ExecutionResources
from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.errors import NDExecutionUnavailableError
from bijux_vex.core.runtime.execution_session import (
    ExecutionSession,
    ExecutionState,
    derive_session_id,
)
from bijux_vex.core.runtime.vector_execution import RandomnessProfile
from bijux_vex.core.types import ExecutionArtifact, ExecutionRequest
from bijux_vex.domain.execution_requests import plan as plan_builder
from bijux_vex.domain.execution_requests.budget import default_budget
from bijux_vex.infra.adapters.ann_base import AnnExecutionRequestRunner


def start_session(
    artifact: ExecutionArtifact,
    request: ExecutionRequest,
    resources: ExecutionResources,
    randomness: RandomnessProfile | None = None,
    ann_runner: AnnExecutionRequestRunner | None = None,
) -> ExecutionSession:
    if (
        randomness is None
        and request.execution_contract is not ExecutionContract.DETERMINISTIC
    ):
        if ann_runner is None:
            raise NDExecutionUnavailableError(
                message="non_deterministic execution requires ann runner"
            )
        randomness = RandomnessProfile(
            seed=secrets.randbits(32),
            sources=("approximate_execution",),
            bounded=False,
            budget=default_budget(request),
            envelopes=tuple((src, 1.0) for src in ann_runner.randomness_sources),
        )
    plan, execution = plan_builder.build_execution_plan(
        artifact, request, resources, randomness=randomness, ann_runner=ann_runner
    )
    budget = default_budget(request)
    session_id = derive_session_id(
        artifact=artifact,
        request=request,
        plan=plan,
        execution=execution,
        randomness=randomness,
        budget=budget,
        state=ExecutionState.PLANNED,
    )
    return ExecutionSession(
        session_id=session_id,
        artifact=artifact,
        request=request,
        plan=plan,
        execution=execution,
        randomness=randomness,
        budget=budget,
        state=ExecutionState.PLANNED,
    )
