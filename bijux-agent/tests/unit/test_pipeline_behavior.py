from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import asdict
from pathlib import Path
import re
from typing import Any, cast

import pytest
from tests.stubs.file_reader_stub import FileReaderStub
from tests.utils.trace_helpers import default_model_metadata

from bijux_agent.agents.critique.core import CritiqueAgent
from bijux_agent.agents.summarizer import SummarizerAgent
from bijux_agent.agents.summarizer.core import SummarizerResult
from bijux_agent.agents.taskhandler.agent import TaskHandlerAgent
from bijux_agent.agents.validator import ValidatorAgent
from bijux_agent.cli.helpers import build_trace_from_result
from bijux_agent.constants import CONTRACT_VERSION
from bijux_agent.enums import DecisionOutcome
from bijux_agent.pipeline import AuditableDocPipeline
from bijux_agent.pipeline.termination import ExecutionTerminationReason


class SummarizerStub(SummarizerAgent):
    """Deterministic summarizer used by pipeline tests."""

    async def _run_payload(self, context: Mapping[str, Any]) -> SummarizerResult:
        summary_text = context.get("text", "stub-summary")
        return {
            "summary": {
                "executive_summary": summary_text,
                "key_points": ["kp-1"],
                "actionable_insights": "n/a",
                "critical_risks": "none",
                "missing_info": "none",
            },
            "method": "stub",
            "input_length": len(str(summary_text)),
            "backend": "stub",
            "strategy": "extractive",
            "warnings": [],
            "audit": {
                "timestamp": "2026-01-01T00:00:00Z",
                "duration_sec": 0.0,
                "input_tokens": len(str(summary_text).split()),
                "output_tokens": len(str(summary_text).split()),
                "chunks_processed": 1,
            },
        }


class ValidatorStub(ValidatorAgent):
    """Deterministic validator used by pipeline tests."""

    async def _run_payload(self, context: Mapping[str, Any]) -> dict[str, Any]:
        payload = {
            "text": context.get("text", "stub"),
            "artifacts": {},
            "scores": {"quality": 1.0},
            "confidence": 0.9,
            "metadata": {"contract_version": CONTRACT_VERSION},
        }
        validated = self.validate_output(payload)
        return validated.model_dump()


class CritiqueStubAgent(CritiqueAgent):
    """Simulate critique feedback required for final validation."""

    async def _run_payload(self, context: Mapping[str, Any]) -> dict[str, Any]:
        payload = {
            "text": "CRITIQUE_READY",
            "artifacts": {"status": "ok"},
            "scores": {"critique": 0.95},
            "confidence": 0.95,
            "metadata": {
                "contract_version": CONTRACT_VERSION,
                "critique_status": "ok",
                "score": 0.95,
                "per_criterion": [],
            },
        }
        validated = self.validate_output(payload)
        result = validated.model_dump()
        result.update(
            critique_status="ok",
            score=0.95,
            per_criterion=[],
        )
        return result


class FakeTaskHandler:
    """Provides deterministic stage outputs for pipeline tests."""

    def __init__(self) -> None:
        self.reset_calls = 0
        self.run_counter = 0
        self.last_payloads: list[str] = []

    def set_stages(self, stages: list[Mapping[str, Any]]) -> None:
        self._stages = stages

    async def run(self, context: dict[str, Any]) -> Mapping[str, Any]:
        self.run_counter += 1
        payload_text = context.get("text", f"shard-{self.run_counter}")
        self.last_payloads.append(payload_text)
        summary_output = {
            "summary": {
                "executive_summary": payload_text.strip(),
                "key_points": [f"kp-{self.run_counter}"],
            },
            "input_length": len(payload_text),
        }
        validation_output = {"valid": True}
        critique_output = {"critique_status": "ok", "score": 0.95, "per_criterion": []}
        return {
            "stages": {
                "summarization": summary_output,
                "validation": validation_output,
                "critique": critique_output,
            },
            "final_status": {
                "success": True,
                "stages_processed": ["summarization"],
                "iterations": 1,
                "termination_reason": ExecutionTerminationReason.COMPLETED,
                "converged": False,
                "convergence_reason": None,
                "convergence_iterations": 0,
            },
            "audit_trail": [
                {
                    "stage_name": f"shard-{self.run_counter}",
                    "timestamp": "2026-01-08T00:00:00Z",
                    "duration_sec": 0.0,
                }
            ],
            "warnings": [],
        }

    def reset_telemetry(self) -> None:
        self.reset_calls += 1


class StatelessTaskHandler(FakeTaskHandler):
    """Task handler that produces identical outputs across invocations."""

    async def run(self, context: dict[str, Any]) -> Mapping[str, Any]:
        payload_text = context.get("text", "stateless")
        self.last_payloads.append(payload_text)
        summary_output = {
            "summary": {
                "executive_summary": payload_text.strip(),
                "key_points": ["kp"],
            },
            "input_length": len(payload_text),
        }
        validation_output = {"valid": True}
        critique_output = {"critique_status": "ok", "score": 0.95, "per_criterion": []}
        return {
            "stages": {
                "summarization": summary_output,
                "validation": validation_output,
                "critique": critique_output,
            },
            "final_status": {
                "success": True,
                "stages_processed": ["summarization"],
                "iterations": 1,
                "termination_reason": ExecutionTerminationReason.COMPLETED,
                "converged": False,
                "convergence_reason": None,
                "convergence_iterations": 0,
            },
            "audit_trail": [
                {
                    "stage_name": "stateless",
                    "timestamp": "2026-01-08T00:00:00Z",
                    "duration_sec": 0.0,
                }
            ],
            "warnings": [],
        }


class ResourceExhaustionTaskHandler(FakeTaskHandler):
    """TaskHandler that simulates hitting resource limits."""

    async def run(self, context: dict[str, Any]) -> Mapping[str, Any]:
        self.run_counter += 1
        payload_text = context.get("text", f"resource-shard-{self.run_counter}")
        summary_output = {
            "summary": {
                "executive_summary": payload_text.strip(),
                "key_points": [f"kp-{self.run_counter}"],
            },
            "input_length": len(payload_text),
        }
        validation_output = {"valid": False}
        critique_output = {
            "critique_status": "needs_revision",
            "score": 0.4,
            "per_criterion": [],
        }
        return {
            "stages": {
                "summarization": summary_output,
                "validation": validation_output,
                "critique": critique_output,
            },
            "final_status": {
                "success": False,
                "stages_processed": ["summarization"],
                "iterations": self.run_counter,
                "termination_reason": ExecutionTerminationReason.RESOURCE_EXHAUSTION,
                "converged": False,
                "convergence_reason": None,
                "convergence_iterations": 0,
            },
            "audit_trail": [
                {
                    "stage_name": f"resource-{self.run_counter}",
                    "timestamp": "2026-01-08T00:00:00Z",
                    "duration_sec": 0.0,
                    "error": "timeout",
                }
            ],
            "warnings": ["timeout"],
            "error": "timeout",
        }


def _shard_payload_key(payload: str) -> int:
    match = re.search(r"Shard (\d+)", payload)
    if not match:
        return 0
    return int(match.group(1))


def make_pipeline(
    handler: FakeTaskHandler,
    logger_manager,
) -> AuditableDocPipeline:
    file_reader_stub = FileReaderStub(logger_manager)
    summarizer_stub = SummarizerStub({}, logger_manager)
    validator_stub = ValidatorStub({}, logger_manager)
    config = {
        "enable_cache": False,
        "pipeline": {
            "parameters": {
                "shard_threshold": 5,
                "max_iterations": 1,
            }
        },
    }
    return AuditableDocPipeline(
        config=config,
        logger_manager=logger_manager,
        task_handler_agent=cast(TaskHandlerAgent, handler),
        file_reader_agent=file_reader_stub,
        summarizer_agent=summarizer_stub,
        validator_agent=validator_stub,
        critique_agent=CritiqueStubAgent({}, logger_manager),
        results_dir=str(Path("artifacts/test/pipeline_results")),
    )


@pytest.mark.asyncio
async def test_pipeline_concurrency_produces_deterministic_ordering(
    logger_manager,
) -> None:
    handler = FakeTaskHandler()
    pipeline = make_pipeline(handler, logger_manager)
    context = {
        "task_goal": "summarize text",
        "text": "\n\n".join(f"Shard {idx}" for idx in range(1, 7)),
    }

    handler.last_payloads = []
    first_result = await pipeline.run(context)
    first_payloads = list(handler.last_payloads)
    assert first_payloads == sorted(first_payloads, key=_shard_payload_key)
    handler.last_payloads = []
    second_result = await pipeline.run(context)

    summary = first_result["stages"]["summarization"]["summary"]["executive_summary"]
    assert summary == "Shard 1 Shard 2 Shard 3 Shard 4 Shard 5 Shard 6"
    assert (
        first_result["telemetry"]["stages_executed"]
        == second_result["telemetry"]["stages_executed"]
    )
    assert (
        first_result["telemetry"]["shards_processed"]
        == second_result["telemetry"]["shards_processed"]
    )
    assert handler.last_payloads == first_payloads


@pytest.mark.asyncio
async def test_pipeline_telemetry_reset_between_runs(logger_manager) -> None:
    handler = FakeTaskHandler()
    pipeline = make_pipeline(handler, logger_manager)
    first_context = {
        "task_goal": "summarize once",
        "text": "Alpha\n\nBeta",
    }
    handler.last_payloads = []
    await pipeline.run(first_context)
    pipeline.reset_telemetry()
    second_context = {
        "task_goal": "summarize twice",
        "text": "Gamma\n\nDelta",
    }
    handler.last_payloads = []
    result = await pipeline.run(second_context)

    assert handler.reset_calls == 3
    assert handler.last_payloads == ["Gamma", "Delta"]
    assert result["telemetry"]["shards_processed"] >= 2
    assert result["telemetry"]["stages_executed"] >= 1


@pytest.mark.asyncio
async def test_pipeline_has_no_hidden_state_between_runs(logger_manager) -> None:
    handler = StatelessTaskHandler()
    pipeline = make_pipeline(handler, logger_manager)
    context = {
        "task_goal": "summarize stateless text",
        "text": "consistent input",
    }

    first_result = await pipeline.run(dict(context))
    second_result = await pipeline.run(dict(context))

    assert first_result["result"] == second_result["result"]
    assert first_result["stages"] == second_result["stages"]
    assert first_result["final_status"] == second_result["final_status"]
    assert first_result["warnings"] == second_result["warnings"]


@pytest.mark.asyncio
async def test_resource_exhaustion_sets_termination_reason(
    logger_manager, tmp_path: Path
) -> None:
    handler = ResourceExhaustionTaskHandler()
    pipeline = make_pipeline(handler, logger_manager)
    context = {
        "task_goal": "fail resource limits",
        "text": "\n\n".join("Resource shard" for _ in range(3)),
    }
    result = await pipeline.run(context)
    final_status = result["final_status"]
    assert (
        final_status["termination_reason"]
        == ExecutionTerminationReason.RESOURCE_EXHAUSTION
    )
    assert not final_status["success"]
    assert final_status["error"] == "timeout"

    trace_dir = tmp_path / "resource_trace"
    trace_dir.mkdir(parents=True, exist_ok=True)
    _, trace = build_trace_from_result(
        pipeline_result=result,
        file_path="resource.txt",
        task_goal=context["task_goal"],
        config={"model_metadata": asdict(default_model_metadata())},
        verdict=DecisionOutcome.VETO,
        confidence=float(final_status.get("score", 0.0)),
        trace_dir=trace_dir,
        convergence_hash=None,
        convergence_reason=None,
        termination_reason=final_status["termination_reason"],
    )
    trace_data = trace.to_dict()
    assert trace_data["entries"]
    assert (
        trace_data["termination_reason"]
        == ExecutionTerminationReason.RESOURCE_EXHAUSTION.value
    )
    assert (
        trace_data["entries"][-1]["termination_reason"]
        == ExecutionTerminationReason.RESOURCE_EXHAUSTION.value
    )


@pytest.mark.asyncio
async def test_async_trace_ordering_deterministic(
    logger_manager, tmp_path: Path
) -> None:
    context_text = "\n\n".join(f"Async Shard {i}" for i in range(1, 7))

    async def run_instance(run_id: str) -> list[str]:
        handler = FakeTaskHandler()
        pipeline = make_pipeline(handler, logger_manager)
        context = {"task_goal": f"async-{run_id}", "text": context_text}
        result = await pipeline.run(context)
        trace_dir = tmp_path / f"trace-{run_id}"
        trace_dir.mkdir(parents=True, exist_ok=True)
        _, trace = build_trace_from_result(
            pipeline_result=result,
            file_path=f"async-{run_id}.txt",
            task_goal=context["task_goal"],
            config={"model_metadata": asdict(default_model_metadata())},
            verdict=DecisionOutcome.PASS
            if result["final_status"]["success"]
            else DecisionOutcome.VETO,
            confidence=float(result["final_status"].get("score", 0.0)),
            trace_dir=trace_dir,
            convergence_hash=None,
            convergence_reason=None,
            termination_reason=result["final_status"].get("termination_reason"),
        )
        return [entry["phase"] for entry in trace.to_dict()["entries"]]

    first_phases, second_phases = await asyncio.gather(
        run_instance("a"), run_instance("b")
    )
    assert first_phases == second_phases
