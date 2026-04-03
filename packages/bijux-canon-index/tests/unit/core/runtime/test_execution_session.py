# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.execution_intent import ExecutionIntent
from bijux_vex.core.execution_mode import ExecutionMode
from bijux_vex.core.runtime.execution_plan import ExecutionPlan
from bijux_vex.core.runtime.execution_session import (
    ExecutionSession,
    ExecutionState,
    derive_session_id,
)
from bijux_vex.core.types import ExecutionArtifact, ExecutionBudget, ExecutionRequest
from bijux_vex.core.runtime.vector_execution import VectorExecution


def test_session_id_is_deterministic():
    artifact = ExecutionArtifact(
        artifact_id="art",
        corpus_fingerprint="corp",
        vector_fingerprint="vec",
        metric="l2",
        scoring_version="v1",
        execution_contract=ExecutionContract.DETERMINISTIC,
    )
    request = ExecutionRequest(
        request_id="r1",
        text=None,
        vector=(0.0,),
        top_k=1,
        execution_contract=ExecutionContract.DETERMINISTIC,
        execution_intent=ExecutionIntent.EXACT_VALIDATION,
        execution_mode=ExecutionMode.STRICT,
    )
    plan = ExecutionPlan(
        algorithm="exact_vector_execution",
        contract=request.execution_contract,
        k=1,
        scoring_fn="l2",
    )
    exec_obj = VectorExecution(
        request=request,
        contract=request.execution_contract,
        backend_id="b",
        algorithm="a",
        parameters=(),
        randomness=None,
        plan=plan,
    )
    sid1 = derive_session_id(
        artifact=artifact,
        request=request,
        plan=plan,
        execution=exec_obj,
        randomness=None,
        budget={},
    )
    sid2 = derive_session_id(
        artifact=artifact,
        request=request,
        plan=plan,
        execution=exec_obj,
        randomness=None,
        budget={},
    )
    assert sid1 == sid2
    session = ExecutionSession(
        session_id=sid1,
        artifact=artifact,
        request=request,
        plan=plan,
        execution=exec_obj,
        randomness=None,
        budget={},
        state=ExecutionState.CREATED,
    )
    assert session.session_id == sid1
