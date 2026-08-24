# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Tests for operation boundaries in concrete Runtime request plans."""

from __future__ import annotations

from bijux_canon_runtime.application.request_planner import RuntimeRequestPlanner
from bijux_canon_runtime.model.execution.request_plan import (
    DagOperation,
    ExecutionProfile,
    RuntimeOperationRequest,
    RuntimeOutputPolicy,
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


def test_offline_lexical_plans_never_schedule_embedding_or_dense_work() -> None:
    planner = RuntimeRequestPlanner()
    index_request = _index_request()
    index_plan = planner.plan(
        RuntimeOperationRequest(
            request_id=index_request.request_id,
            operation=index_request.operation,
            execution_profile=ExecutionProfile.OFFLINE_LEXICAL,
            budget=index_request.budget,
            replay_mode=index_request.replay_mode,
            scope=index_request.scope,
            corpus_id=index_request.corpus_id,
        )
    )

    assert tuple(step.operation for step in index_plan.steps) == (
        DagOperation.LEXICAL_INDEX,
    )
    assert index_plan.steps[0].output_artifact_contract_ids == ("index.lexical.v1",)

    for operation in (
        RuntimeRequestOperation.RETRIEVE,
        RuntimeRequestOperation.ASK,
        RuntimeRequestOperation.RESEARCH,
    ):
        request = RuntimeOperationRequest(
            request_id=RequestID(f"request-{operation.value}"),
            operation=operation,
            execution_profile=ExecutionProfile.OFFLINE_LEXICAL,
            budget=index_request.budget,
            replay_mode=ReplayMode.STRICT,
            scope="local",
            query="What evidence is retained?",
            index_id=ArtifactID("sha256:" + "b" * 64),
            top_k=3,
            provider=(
                None
                if operation is RuntimeRequestOperation.RETRIEVE
                else "credential-free"
            ),
            output_policy=(
                None
                if operation is RuntimeRequestOperation.RETRIEVE
                else RuntimeOutputPolicy(True, True, True)
            ),
        )
        plan = planner.plan(request)
        assert all(
            step.operation not in {DagOperation.EMBED, DagOperation.DENSE_INDEX}
            for step in plan.steps
        )
        retrieve = next(
            step for step in plan.steps if step.operation is DagOperation.RETRIEVE
        )
        assert retrieve.input_artifact_contract_ids == ("index.lexical.v1",)
