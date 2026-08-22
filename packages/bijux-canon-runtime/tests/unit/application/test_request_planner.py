# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Tests for operation boundaries in concrete Runtime request plans."""

from __future__ import annotations

from bijux_canon_runtime.application.request_planner import RuntimeRequestPlanner
from bijux_canon_runtime.model.execution.request_plan import (
    DagOperation,
    ExecutionProfile,
    RuntimeOperationRequest,
    RuntimeRequestBudget,
    RuntimeRequestOperation,
)
from bijux_canon_runtime.ontology.ids import ArtifactID, RequestID
from bijux_canon_runtime.ontology.public import ReplayMode


def _index_request() -> RuntimeOperationRequest:
    return RuntimeOperationRequest(
        request_id=RequestID("request-index-boundaries"),
        operation=RuntimeRequestOperation.INDEX_BUILD,
        execution_profile=ExecutionProfile.LOCAL_HYBRID_ANN,
        budget=RuntimeRequestBudget(
            timeout_seconds=30.0,
            max_artifact_bytes=10_000_000,
        ),
        replay_mode=ReplayMode.STRICT,
        scope="local",
        corpus_id=ArtifactID("sha256:" + "a" * 64),
    )


def test_index_plan_keeps_lexical_and_embedding_work_independent() -> None:
    plan = RuntimeRequestPlanner().plan(_index_request())
    steps = {step.operation: step for step in plan.steps}

    assert steps[DagOperation.EMBED].depends_on == ()
    assert steps[DagOperation.LEXICAL_INDEX].depends_on == ()
    assert steps[DagOperation.DENSE_INDEX].depends_on == (
        "embed",
        "lexical_index",
    )
    assert steps[DagOperation.DENSE_INDEX].input_artifact_contract_ids == (
        "index.embedding-matrix.v1",
        "index.lexical.v1",
    )
    assert steps[DagOperation.DENSE_INDEX].output_artifact_contract_ids == (
        "index.composite.v1",
    )
    assert plan.entry_step_ids == ("embed", "lexical_index")
    assert plan.terminal_step_ids == ("dense_index",)
