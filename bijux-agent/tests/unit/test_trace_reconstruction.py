from __future__ import annotations

import gc
from pathlib import Path

import pytest
from tests.utils.trace_helpers import default_model_metadata

from bijux_agent.cli.helpers import load_trace
from bijux_agent.constants import CONTRACT_VERSION
from bijux_agent.enums import DecisionOutcome
from bijux_agent.models.contract import AgentInputSchema, AgentOutputSchema
from bijux_agent.orchestrator.engine import AgentNode, Orchestrator
from bijux_agent.orchestrator.policy import FailurePolicy
from bijux_agent.pipeline.epistemic import EpistemicVerdict
from bijux_agent.pipeline.results.outcome import PipelineResult, PipelineStatus


@pytest.mark.asyncio
async def test_trace_reconstructs_result_after_runtime_cleanup(tmp_path: Path) -> None:
    """Pipeline outcomes must be recoverable from traces even after the runtime is gone."""

    async def initial_runner(context: AgentInputSchema) -> AgentOutputSchema:
        return AgentOutputSchema(
            text="initial output",
            artifacts={"step": "initial"},
            scores={"initial": 0.6},
            confidence=0.6,
            metadata={"contract_version": CONTRACT_VERSION},
        )

    async def final_runner(context: AgentInputSchema) -> AgentOutputSchema:
        return AgentOutputSchema(
            text="final output",
            artifacts={"step": "final"},
            scores={"final": 0.8},
            confidence=0.82,
            metadata={"contract_version": CONTRACT_VERSION},
        )

    nodes = [
        AgentNode(name="initial", runner=initial_runner),
        AgentNode(
            name="final",
            runner=final_runner,
            dependencies=["initial"],
        ),
    ]

    orchestrator = Orchestrator(
        nodes=nodes,
        trace_path=tmp_path / "reconstruct_trace.json",
        failure_policy=FailurePolicy(),
        model_metadata=default_model_metadata(),
    )
    initial = AgentInputSchema(
        task_goal="demonstrate trace recovery",
        payload={},
        context_id="trace-cleanup",
        metadata={"contract_version": CONTRACT_VERSION},
    )

    await orchestrator.run(initial)
    trace = orchestrator.trace_recorder.trace
    final_confidence = float(trace.entries[-1].output["confidence"])
    trace_path = tmp_path / "reconstruct_trace.json"
    del orchestrator
    initial_runner = None
    final_runner = None
    gc.collect()

    reloaded_trace = load_trace(trace_path)
    rehydrated = PipelineResult.from_trace(reloaded_trace)

    reconstructed = PipelineResult.from_trace(trace)
    metadata = trace.header.model_metadata
    assert metadata is not None
    expected = PipelineResult(
        status=PipelineStatus.DONE,
        decision=DecisionOutcome.APPROVE,
        epistemic_verdict=EpistemicVerdict.CERTAIN,
        confidence=final_confidence,
        model_metadata=metadata,
    )

    assert reconstructed == expected
    assert rehydrated == expected
