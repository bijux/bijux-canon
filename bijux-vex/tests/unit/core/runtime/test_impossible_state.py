# SPDX-License-Identifier: MIT
# SPDX-License-Identifier: MIT
from __future__ import annotations
import pytest

from bijux_vex.core.execution_intent import ExecutionIntent
from bijux_vex.core.execution_mode import ExecutionMode
from bijux_vex.core.errors import InvariantError
from bijux_vex.core.runtime.execution_session import ExecutionSession, ExecutionState
from bijux_vex.core.types import ExecutionArtifact, ExecutionRequest
from bijux_vex.core.contracts.execution_contract import ExecutionContract


def test_execution_session_cannot_start_without_plan():
    artifact = ExecutionArtifact(
        artifact_id="a",
        corpus_fingerprint="c",
        vector_fingerprint="v",
        metric="l2",
        scoring_version="v1",
        execution_contract=ExecutionContract.DETERMINISTIC,
    )
    request = ExecutionRequest(
        request_id="r",
        text=None,
        vector=(0.1,),
        top_k=1,
        execution_contract=ExecutionContract.DETERMINISTIC,
        execution_intent=ExecutionIntent.EXACT_VALIDATION,
        execution_mode=ExecutionMode.STRICT,
    )
    with pytest.raises(TypeError):
        ExecutionSession(
            artifact=artifact,
            request=request,
            plan=None,  # type: ignore[arg-type]
            execution=None,  # type: ignore[arg-type]
            state=ExecutionState.CREATED,
            budget=None,
        )
