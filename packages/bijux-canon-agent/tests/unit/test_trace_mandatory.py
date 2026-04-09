from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from bijux_canon_agent.application.workflow_graph.orchestrator import (
    WorkflowNode,
    WorkflowOrchestrator,
)
from bijux_canon_agent.application.workflow_graph.policy import FailurePolicy
from bijux_canon_agent.constants import CONTRACT_VERSION
from bijux_canon_agent.contracts.agent_contract import (
    AgentInputSchema,
    AgentOutputSchema,
)
import pytest
from tests.utils.trace_helpers import default_model_metadata


def _drop_trace_entry(record_fn: Callable, target_node: str) -> Callable:
    dropped = {"seen": False}

    def wrapper(entry: object) -> None:
        if getattr(entry, "node", "") == target_node and not dropped["seen"]:
            dropped["seen"] = True
            return None
        return record_fn(entry)

    return wrapper


@pytest.mark.asyncio
async def test_trace_is_mandatory(tmp_path: Path) -> None:
    """Missing trace entries must invalidate the run before completion."""

    async def simple_runner(context: AgentInputSchema) -> AgentOutputSchema:
        return AgentOutputSchema(
            text="ok",
            artifacts={},
            scores={"ok": 1.0},
            confidence=0.8,
            metadata={"contract_version": CONTRACT_VERSION},
        )

    nodes = [
        WorkflowNode(name="node_one", runner=simple_runner),
        WorkflowNode(
            name="node_two",
            runner=simple_runner,
            dependencies=["node_one"],
        ),
    ]
    orchestrator = WorkflowOrchestrator(
        nodes=nodes,
        trace_path=tmp_path / "mandatory.json",
        failure_policy=FailurePolicy(),
        model_metadata=default_model_metadata(),
    )
    orchestrator.trace_recorder.record_entry = _drop_trace_entry(
        orchestrator.trace_recorder.record_entry, target_node="node_two"
    )
    initial_input = AgentInputSchema(
        task_goal="require trace",
        payload={},
        context_id="ctx-mandatory",
        metadata={"contract_version": CONTRACT_VERSION},
    )

    with pytest.raises(RuntimeError):
        await orchestrator.run(initial_input)
