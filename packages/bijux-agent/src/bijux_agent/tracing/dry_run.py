"""Deterministic dry-run trace generator for contract tests."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime, timedelta
import hashlib
import json
from pathlib import Path
from typing import Any

from bijux_agent.constants import CONTRACT_VERSION
from bijux_agent.enums import AgentType, DecisionOutcome
from bijux_agent.pipeline.control.phases import PipelinePhase
from bijux_agent.pipeline.convergence.monitor import (
    ConvergenceMonitor,
    default_convergence_config,
)
from bijux_agent.pipeline.definition import (
    PipelineDefinition,
    standard_pipeline_definition,
)
from bijux_agent.pipeline.epistemic import EpistemicVerdict
from bijux_agent.pipeline.results.decision import DecisionArtifact
from bijux_agent.pipeline.tracing.trace_validator import TraceValidator
from bijux_agent.tracing.trace import (
    EpistemicStatus,
    ModelMetadata,
    ReplayMetadata,
    RunFingerprint,
    RunTrace,
    RunTraceHeader,
    TraceEntry,
)

_PHASE_AGENT: dict[PipelinePhase, AgentType] = {
    PipelinePhase.PLAN: AgentType.PLANNER,
    PipelinePhase.EXECUTE: AgentType.READER,
    PipelinePhase.JUDGE: AgentType.JUDGE,
    PipelinePhase.VERIFY: AgentType.VERIFIER,
    PipelinePhase.FINALIZE: AgentType.ORCHESTRATOR,
}


def _phase_sequence(definition: PipelineDefinition) -> list[PipelinePhase]:
    return [
        phase
        for phase in definition.phases
        if phase not in (PipelinePhase.INIT, PipelinePhase.DONE)
    ]


def generate_dry_run_trace(
    *,
    run_id: str = "dry-run",
    definition: PipelineDefinition | None = None,
    config: dict[str, Any] | None = None,
    base_time: datetime | None = None,
    runtime_version: str = "dry-run",
) -> RunTrace:
    """Generate a synthetic but valid trace without calling any models."""
    definition = definition or standard_pipeline_definition()
    base_time = base_time or datetime(2024, 1, 1, tzinfo=UTC)
    config_payload = json.dumps(config or {"mode": "dry-run"}, sort_keys=True)
    config_hash = hashlib.sha256(config_payload.encode()).hexdigest()
    fingerprint = RunFingerprint.create(definition, config or {"mode": "dry-run"})

    convergence = ConvergenceMonitor(config=default_convergence_config())
    convergence.record({"quality": 0.9}, DecisionOutcome.PASS, 0.92)
    convergence.record({"quality": 0.901}, DecisionOutcome.PASS, 0.921)
    convergence.record({"quality": 0.9015}, DecisionOutcome.PASS, 0.9215)

    model_metadata = ModelMetadata(
        provider="dry-run",
        model_name="dry-run-model",
        temperature=0.0,
        max_tokens=512,
    )

    header = RunTraceHeader(
        config_hash=config_hash,
        pipeline_definition_hash=hashlib.sha256(
            json.dumps(definition.to_payload(), sort_keys=True).encode()
        ).hexdigest(),
        agent_versions={"pipeline": "dry-run"},
        runtime_version=runtime_version,
        convergence_hash=convergence.convergence_hash or "",
        convergence_reason=convergence.convergence_reason.value
        if convergence.convergence_reason
        else None,
        model_metadata=model_metadata,
    )

    entries: list[TraceEntry] = []
    for idx, phase in enumerate(_phase_sequence(definition)):
        start_time = base_time + timedelta(minutes=idx)
        end_time = start_time + timedelta(seconds=30)
        agent_type = _PHASE_AGENT.get(phase, AgentType.PLANNER)
        prompt_seed = f"dry-run:{phase.value}"
        prompt_hash = hashlib.sha256(prompt_seed.encode()).hexdigest()
        model_hash = hashlib.sha256(f"model:{phase.value}".encode()).hexdigest()
        decision = DecisionOutcome.PASS.value
        output = {
            "text": f"{phase.value} result",
            "artifacts": {"phase": phase.value},
            "scores": {"quality": 0.8 + idx * 0.01},
            "confidence": round(0.8 + idx * 0.01, 3),
            "metadata": {
                "contract_version": CONTRACT_VERSION,
                "model_metadata": asdict(model_metadata),
            },
            "decision": decision,
        }
        entry = TraceEntry(
            agent_id=f"{agent_type.value}-agent",
            node=phase.value.lower(),
            status="success",
            start_time=start_time,
            end_time=end_time,
            input={"phase": phase.value, "agent_type": agent_type.value},
            output=output,
            scores={"quality": 0.8 + idx * 0.01},
            prompt_hash=prompt_hash,
            model_hash=model_hash,
            phase=phase.value,
            run_id=run_id,
            replay_metadata=ReplayMetadata(
                input_hash=hashlib.sha256(
                    f"{run_id}:{phase.value}".encode()
                ).hexdigest(),
                config_hash=config_hash,
                model_id=f"dry-run:{phase.value}",
                convergence_hash=header.convergence_hash,
                model_metadata=model_metadata,
            ),
            run_fingerprint=fingerprint if phase == PipelinePhase.FINALIZE else None,
        )
        if phase == PipelinePhase.FINALIZE:
            entry.decision_artifact = DecisionArtifact(
                verdict=DecisionOutcome.PASS,
                justification="dry-run success",
                supporting_trace_ids=[run_id],
            )
            entry.epistemic_status = EpistemicStatus(
                status="certain", justification="dry-run"
            )
            entry.epistemic_verdict = EpistemicVerdict.CERTAIN
        entries.append(entry)

    TraceValidator.validate(
        entries,
        definition,
        stop_reason=None,
        header=header,
    )

    return RunTrace(
        run_id=run_id,
        started_at=base_time,
        completed_at=entries[-1].end_time if entries else base_time,
        status="completed",
        header=header,
        entries=entries,
    )


def write_dry_run_trace(path: Path) -> RunTrace:
    trace = generate_dry_run_trace()
    path.write_text(json.dumps(trace.to_dict(), indent=2), encoding="utf-8")
    return trace
