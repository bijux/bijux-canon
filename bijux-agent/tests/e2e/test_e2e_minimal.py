from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from tests.utils.trace_helpers import (
    build_replay_metadata,
    build_run_fingerprint,
    default_model_metadata,
)

from bijux_agent.agents import JudgeAgent, PlannerAgent, VerifierAgent
from bijux_agent.constants import CONTRACT_VERSION
from bijux_agent.enums import DecisionOutcome
from bijux_agent.models.llm_adapter import AdapterConfig, MockAdapter
from bijux_agent.models.registry import Provider
from bijux_agent.pipeline.control.phases import PipelinePhase
from bijux_agent.tracing import TraceEntry, TraceRecorder
from bijux_agent.utilities.logger_manager import LoggerConfig, LoggerManager


@pytest.mark.asyncio
async def test_end_to_end_minimal_run(tmp_path: Path) -> None:
    logger = LoggerManager(LoggerConfig(log_dir=tmp_path / "logs"))
    planner = PlannerAgent({}, logger)
    judge = JudgeAgent({}, logger)
    verifier = VerifierAgent({}, logger)

    trace_path = tmp_path / "trace.json"
    recorder = TraceRecorder(
        run_id="e2e-minimal",
        path=trace_path,
        model_metadata=default_model_metadata(),
    )

    context = {"task_goal": "summarize policy", "context_id": "run-1", "payload": {}}
    plan_result = await planner.run(context)
    # deterministic plan check
    second_result = await planner.run(context)
    assert plan_result.artifacts["plan"] == second_result.artifacts["plan"]

    now = datetime.now(UTC)
    recorder.record_entry(
        TraceEntry(
            agent_id="PlannerAgent",
            node="planner",
            status="success",
            start_time=now,
            end_time=now,
            input=context,
            output=plan_result,
            scores={"quality": plan_result.scores.get("quality", 0.0)},
            phase=PipelinePhase.PLAN.value,
            prompt_hash="plan-hash",
            model_hash="planner-model",
            run_id="e2e-minimal",
            replay_metadata=build_replay_metadata(model_id="planner"),
            run_fingerprint=build_run_fingerprint(),
        )
    )

    # simulate downstream outputs using MockAdapter
    mock_config = AdapterConfig(
        provider=Provider.MOCK.value,
        model_name="mock-model",
        temperature=0.0,
        max_tokens=512,
    )
    adapter = MockAdapter(mock_config, canned_response="Verified: {prompt}")
    raw_outputs = []
    for i in range(2):
        response = adapter.generate("test prompt")
        raw_outputs.append(
            {
                "text": response.text,
                "artifacts": {"run": i},
                "scores": {"correctness": 0.9, "risk": 0.1},
                "confidence": 0.9,
                "metadata": {"evidence": True, "contract_version": CONTRACT_VERSION},
                "decision": DecisionOutcome.PASS.value,
            }
        )

    judge_context = {
        "task_goal": "summarize policy",
        "context_id": "run-judge",
        "payload": {"agent_outputs": raw_outputs},
    }
    judge_result = await judge.run(judge_context)
    recorder.record_entry(
        TraceEntry(
            agent_id="JudgeAgent",
            node="judge",
            status="success",
            start_time=now,
            end_time=now,
            input=judge_context,
            output=judge_result,
            scores={"quality": judge_result.scores.get("quality", 0.0)},
            phase=PipelinePhase.JUDGE.value,
            prompt_hash="hash-judge",
            model_hash="mock-model",
            run_id="e2e-minimal",
            replay_metadata=build_replay_metadata(model_id="judge"),
            run_fingerprint=build_run_fingerprint(),
        )
    )

    verifier_context = {
        "task_goal": "summarize policy",
        "context_id": "run-verifier",
        "payload": {"agent_outputs": raw_outputs},
    }
    verifier_result = await verifier.run(verifier_context)
    recorder.record_entry(
        TraceEntry(
            agent_id="VerifierAgent",
            node="verifier",
            status="success",
            start_time=now,
            end_time=now,
            input=verifier_context,
            output=verifier_result,
            scores={"quality": verifier_result.scores.get("quality", 0.0)},
            phase=PipelinePhase.VERIFY.value,
            prompt_hash="hash-verifier",
            model_hash="mock-model",
            run_id="e2e-minimal",
            replay_metadata=build_replay_metadata(model_id="verifier"),
            run_fingerprint=build_run_fingerprint(),
        )
    )

    recorder.finish(status="completed")

    assert trace_path.exists()
    data = trace_path.read_text(encoding="utf-8")
    assert "e2e-minimal" in data
    assert judge_result.metadata.get("decision") == DecisionOutcome.PASS.value
    assert verifier_result.metadata.get("decision") == DecisionOutcome.PASS.value
    assert "aggregated_scores" in judge_result.artifacts
