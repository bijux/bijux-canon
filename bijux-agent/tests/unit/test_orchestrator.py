from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from tests.utils.trace_helpers import default_model_metadata

from bijux_agent.constants import CONTRACT_VERSION
from bijux_agent.enums import PipelineState
from bijux_agent.models.contract import AgentInputSchema, AgentOutputSchema
from bijux_agent.orchestrator.engine import AgentNode, Orchestrator
from bijux_agent.orchestrator.policy import (
    FailurePolicy,
    ScopeReductionPolicy,
)
from bijux_agent.orchestrator.state_machine import OrchestratorStateMachine
from bijux_agent.pipeline.control.stop_conditions import StopReason


@pytest.mark.asyncio
async def test_orchestrator_run_happy_path(tmp_path: Path) -> None:
    """Orchestrator should execute nodes in dependency order and complete."""

    async def fake_runner(context: AgentInputSchema) -> AgentOutputSchema:
        return AgentOutputSchema(
            text="ok",
            artifacts={},
            scores={"ok": 1.0},
            confidence=0.75,
            metadata={"contract_version": CONTRACT_VERSION},
        )

    node = AgentNode(name="node1", runner=fake_runner)
    orchestrator = Orchestrator(
        nodes=[node],
        trace_path=tmp_path / "trace.json",
        failure_policy=FailurePolicy(),
        model_metadata=default_model_metadata(),
    )
    initial = AgentInputSchema(
        task_goal="validate something",
        payload={},
        context_id="ctx-1",
        metadata={"contract_version": CONTRACT_VERSION},
    )
    state = await orchestrator.run(initial)
    assert state.completed["node1"].text == "ok"
    assert not state.aborted
    assert orchestrator.trace_recorder.trace.status == "completed"
    assert orchestrator.trace_recorder.trace.entries[-1].status == "success"


@pytest.mark.asyncio
async def test_orchestrator_abort_records_stop_reason(tmp_path: Path) -> None:
    """Abort path should record a StopReason on the last trace entry."""

    class StopSignalError(RuntimeError):
        code = "FATAL"
        stop_reason = StopReason.USER_INTERRUPTION

    async def stop_runner(context: AgentInputSchema) -> AgentOutputSchema:
        raise StopSignalError("manual stop requested")

    node = AgentNode(name="stopper", runner=stop_runner, max_retries=1)
    orchestrator = Orchestrator(
        nodes=[node],
        trace_path=tmp_path / "stop_trace.json",
        failure_policy=FailurePolicy(),
        model_metadata=default_model_metadata(),
    )
    initial = AgentInputSchema(
        task_goal="abort scenario",
        payload={},
        context_id="ctx-abort",
        metadata={"contract_version": CONTRACT_VERSION},
    )

    state = await orchestrator.run(initial)
    assert state.aborted
    last_entry = orchestrator.trace_recorder.trace.entries[-1]
    assert last_entry.stop_reason == StopReason.USER_INTERRUPTION


@pytest.mark.asyncio
async def test_orchestrator_partial_failure_stops_downstream(tmp_path: Path) -> None:
    """A failing node should abort and prevent downstream execution."""

    async def failing_runner(context: AgentInputSchema) -> AgentOutputSchema:
        raise RuntimeError("simulated failure")

    async def never_run(context: AgentInputSchema) -> AgentOutputSchema:
        raise AssertionError("Downstream node must not run")

    nodes = [
        AgentNode(name="fail_step", runner=failing_runner, max_retries=1),
        AgentNode(
            name="dependent",
            runner=never_run,
            dependencies=["fail_step"],
        ),
    ]
    orchestrator = Orchestrator(
        nodes=nodes,
        trace_path=tmp_path / "partial_failure.json",
        failure_policy=FailurePolicy(),
        model_metadata=default_model_metadata(),
    )
    initial = AgentInputSchema(
        task_goal="handle failure",
        payload={},
        context_id="ctx-partial",
        metadata={"contract_version": CONTRACT_VERSION},
    )
    state = await orchestrator.run(initial)
    assert state.aborted
    assert "dependent" not in state.completed
    assert state.errors.get("fail_step")
    trace = orchestrator.trace_recorder.trace
    assert trace.status == "aborted"
    assert trace.entries[-1].status == "failed"


@pytest.mark.asyncio
async def test_orchestrator_retry_policy_retries_until_success(tmp_path: Path) -> None:
    """Retry policy should allow a node to recover after a transient failure."""

    attempts: dict[str, int] = {"count": 0}

    async def flaky_runner(context: AgentInputSchema) -> AgentOutputSchema:
        if attempts["count"] < 1:
            attempts["count"] += 1
            raise RuntimeError("first attempt fails")
        return AgentOutputSchema(
            text="recovered",
            artifacts={},
            scores={"ok": 1.0},
            confidence=0.8,
            metadata={"contract_version": CONTRACT_VERSION},
        )

    node = AgentNode(name="retry_step", runner=flaky_runner)
    orchestrator = Orchestrator(
        nodes=[node],
        trace_path=tmp_path / "retry_trace.json",
        failure_policy=FailurePolicy(),
        model_metadata=default_model_metadata(),
    )
    initial = AgentInputSchema(
        task_goal="retry scenario",
        payload={},
        context_id="ctx-retry",
        metadata={"contract_version": CONTRACT_VERSION},
    )
    state = await orchestrator.run(initial)
    assert not state.aborted
    assert state.attempts["retry_step"] == 2
    assert state.completed["retry_step"].text == "recovered"
    trace = orchestrator.trace_recorder.trace
    assert len(trace.entries) == 2


@pytest.mark.asyncio
async def test_scope_reduction_policy_reduces_payload(tmp_path: Path) -> None:
    """Scope reduction steps should shrink the payload before each agent runs."""

    observed_payloads: list[dict[str, Any]] = []

    async def observing_runner(context: AgentInputSchema) -> AgentOutputSchema:
        observed_payloads.append(dict(context.payload))
        return AgentOutputSchema(
            text="ok",
            artifacts={},
            scores={"ok": 1.0},
            confidence=0.75,
            metadata={"contract_version": CONTRACT_VERSION},
        )

    policy = FailurePolicy(
        scope_reduction=ScopeReductionPolicy(steps=["drop:secret_key"])
    )
    node = AgentNode(name="node", runner=observing_runner)
    orchestrator = Orchestrator(
        nodes=[node],
        trace_path=tmp_path / "scope_trace.json",
        failure_policy=policy,
        model_metadata=default_model_metadata(),
    )
    initial = AgentInputSchema(
        task_goal="scope reduction",
        payload={"secret_key": "top", "keep": "value"},
        context_id="ctx-scope",
        metadata={"contract_version": CONTRACT_VERSION},
    )
    await orchestrator.run(initial)
    assert observed_payloads, "Runner should have executed at least once"
    for payload in observed_payloads:
        assert "secret_key" not in payload
        assert payload.get("keep") == "value"


def test_orchestrator_state_machine_transitions() -> None:
    """State machine should only allow declared transitions."""
    machine = OrchestratorStateMachine()
    machine.transition_to(PipelineState.RUNNING)
    machine.abort()
    assert machine.state == PipelineState.ABORTED

    machine = OrchestratorStateMachine()
    machine.transition_to(PipelineState.RUNNING)
    machine.transition_to(PipelineState.JUDGING)
    with pytest.raises(RuntimeError):
        machine.transition_to(PipelineState.DONE)
