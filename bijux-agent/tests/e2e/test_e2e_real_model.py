from __future__ import annotations

from datetime import UTC, datetime
import os
from typing import Any

import pytest
from tests.utils.trace_helpers import (
    build_replay_metadata,
    build_run_fingerprint,
    build_trace_header,
)

from bijux_agent.agents import JudgeAgent, PlannerAgent, VerifierAgent
from bijux_agent.agents.base import BaseAgent
from bijux_agent.config.env import key_for_provider, load_environment
from bijux_agent.constants import CONTRACT_VERSION
from bijux_agent.enums import AgentType, DecisionOutcome
from bijux_agent.models.llm_adapter import AdapterConfig, OpenAIAdapter
from bijux_agent.pipeline.control.controller import PipelineController
from bijux_agent.pipeline.control.phases import PipelinePhase
from bijux_agent.pipeline.convergence.monitor import (
    ConvergenceMonitor,
    ConvergenceReason,
    default_convergence_config,
)
from bijux_agent.pipeline.definition import standard_pipeline_definition
from bijux_agent.pipeline.tracing.trace_validator import TraceValidator
from bijux_agent.tracing import RunTrace, TraceEntry
from bijux_agent.utilities.logger_manager import LoggerConfig, LoggerManager

RUN_REAL_MODEL_TESTS = os.getenv("RUN_REAL_MODEL_TESTS") == "1"


class RealExecutorAgent(BaseAgent):
    def __init__(
        self,
        config: dict[str, object],
        logger_manager: LoggerManager,
        adapter: OpenAIAdapter,
    ) -> None:
        super().__init__(config, logger_manager)
        self.adapter = adapter

    def _initialize(self) -> None:
        return None

    def _cleanup(self) -> None:
        return None

    async def _run_payload(self, context: dict[str, Any]) -> dict[str, Any]:
        prompt = context["payload"]["prompt"]
        response = self.adapter.generate(prompt)
        output = {
            "text": response.text,
            "artifacts": {"model": response.model},
            "scores": {"llm_response": 0.95},
            "confidence": response.confidence,
            "metadata": {
                "prompt_hash": response.prompt_hash,
                "contract_version": CONTRACT_VERSION,
            },
            "decision": DecisionOutcome.PASS.value,
        }
        return self.validate_output(output).model_dump()


def _trace_entry_for_phase(
    agent_type: AgentType,
    phase: PipelinePhase,
    input_payload: dict[str, Any],
    output: dict[str, Any],
) -> TraceEntry:
    now = datetime.now(UTC)
    return TraceEntry(
        agent_id=agent_type.name,
        node=agent_type.value,
        status="success",
        start_time=now,
        end_time=now,
        input={"phase": phase.value, "agent_type": agent_type.value, **input_payload},
        output=output,
        scores=output.get("scores", {}),
        prompt_hash=output.get("metadata", {}).get("prompt_hash", ""),
        model_hash=output.get("metadata", {}).get("model", ""),
        phase=phase.value,
        run_id="real-e2e",
        replay_metadata=build_replay_metadata(
            model_id=agent_type.name,
            input_hash=f"{phase.value}-input",
        ),
        run_fingerprint=build_run_fingerprint(),
    )


@pytest.mark.e2e
@pytest.mark.skipif(
    not RUN_REAL_MODEL_TESTS,
    reason="Live real-model pipeline disabled; set RUN_REAL_MODEL_TESTS=1 to execute",
)
@pytest.mark.asyncio
async def test_e2e_real_model_flow(tmp_path) -> None:
    load_environment()
    key_for_provider("OpenAI")  # ensures no missing key

    logger = LoggerManager(LoggerConfig(log_dir=tmp_path / "logs"))
    planner = PlannerAgent({}, logger)
    judge = JudgeAgent({}, logger)
    verifier = VerifierAgent({}, logger)
    executor_adapter = OpenAIAdapter(
        AdapterConfig(
            provider="OpenAI",
            model_name="gpt-3.5-turbo",
            temperature=0.0,
            max_tokens=256,
        )
    )
    executor = RealExecutorAgent({}, logger, executor_adapter)

    controller = PipelineController()
    trace_entries: list[TraceEntry] = []
    convergence = ConvergenceMonitor(config=default_convergence_config())

    context = {
        "task_goal": "Summarize the policy document cleanly",
        "context_id": "real-e2e",
        "payload": {},
    }

    controller.transition_to(PipelinePhase.PLAN)
    plan_result = await planner.run(context)
    trace_entries.append(
        _trace_entry_for_phase(
            AgentType.PLANNER,
            PipelinePhase.PLAN,
            {},
            plan_result,
        )
    )

    plan_artifact = plan_result.artifacts["plan"]
    executor_context = {
        "task_goal": context["task_goal"],
        "context_id": "real-exec",
        "payload": {"prompt": f"{plan_artifact['sequence']}"},
    }
    controller.transition_to(PipelinePhase.EXECUTE)
    executor_result = await executor.run(executor_context)
    convergence.record(
        executor_result["scores"], DecisionOutcome.PASS, executor_result["confidence"]
    )
    trace_entries.append(
        _trace_entry_for_phase(
            AgentType.SUMMARIZER,
            PipelinePhase.EXECUTE,
            executor_context["payload"],
            executor_result,
        )
    )

    judge_context = {
        "task_goal": context["task_goal"],
        "context_id": "real-judge",
        "payload": {"agent_outputs": [executor_result]},
    }
    controller.transition_to(PipelinePhase.JUDGE)
    judge_result = await judge.run(judge_context)
    convergence.record(
        judge_result["scores"], DecisionOutcome.PASS, judge_result["confidence"]
    )
    trace_entries.append(
        _trace_entry_for_phase(
            AgentType.JUDGE,
            PipelinePhase.JUDGE,
            judge_context["payload"],
            judge_result,
        )
    )

    verifier_context = {
        "task_goal": context["task_goal"],
        "context_id": "real-verify",
        "payload": {"agent_outputs": [executor_result]},
    }
    controller.transition_to(PipelinePhase.VERIFY)
    verifier_result = await verifier.run(verifier_context)
    convergence.record(
        verifier_result["scores"],
        DecisionOutcome.PASS,
        verifier_result["confidence"],
    )
    trace_entries.append(
        _trace_entry_for_phase(
            AgentType.VERIFIER,
            PipelinePhase.VERIFY,
            verifier_context["payload"],
            verifier_result,
        )
    )

    controller.transition_to(PipelinePhase.FINALIZE)
    trace_entries.append(
        _trace_entry_for_phase(
            AgentType.ORCHESTRATOR,
            PipelinePhase.FINALIZE,
            {},
            verifier_result,
        )
    )

    trace = RunTrace(
        run_id="real-e2e",
        status="done",
        header=build_trace_header(
            convergence_hash="",
            convergence_reason=ConvergenceReason.STABILITY.value,
        ),
        entries=trace_entries,
    )
    controller.finalize(trace)
    assert controller.phase == PipelinePhase.DONE
    assert not controller.should_stop()
    assert convergence.has_converged()
    convergence_hash = "test-convergence"
    trace_entries[-1].replay_metadata.convergence_hash = convergence_hash
    TraceValidator.validate(
        trace_entries,
        standard_pipeline_definition(),
        stop_reason=None,
        header=build_trace_header(
            convergence_hash=convergence_hash,
            convergence_reason=ConvergenceReason.STABILITY.value,
        ),
    )
    assert verifier_result["confidence"] > 0
    assert "decision" in verifier_result
