from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
import json

from bijux_agent.constants import CONTRACT_VERSION
from bijux_agent.enums import AgentType, DecisionOutcome
from bijux_agent.pipeline.control.phases import PipelinePhase
from bijux_agent.pipeline.convergence.monitor import (
    ConvergenceMonitor,
    default_convergence_config,
)
from bijux_agent.pipeline.definition import standard_pipeline_definition
from bijux_agent.pipeline.epistemic import EpistemicVerdict
from bijux_agent.pipeline.results.decision import DecisionArtifact
from bijux_agent.tracing.dry_run import generate_dry_run_trace
from bijux_agent.tracing.trace import TRACE_SCHEMA_VERSION


def test_dry_run_trace_generator_snapshot() -> None:
    definition = standard_pipeline_definition()
    base_time = datetime(2024, 1, 1, tzinfo=UTC)
    run_id = "dry-run"
    config_payload = json.dumps({"mode": "dry-run"}, sort_keys=True)
    config_hash = hashlib.sha256(config_payload.encode()).hexdigest()
    pipeline_hash = hashlib.sha256(
        json.dumps(definition.to_payload(), sort_keys=True).encode()
    ).hexdigest()

    convergence = ConvergenceMonitor(config=default_convergence_config())
    convergence.record({"quality": 0.9}, DecisionOutcome.PASS, 0.92)
    convergence.record({"quality": 0.901}, DecisionOutcome.PASS, 0.921)
    convergence.record({"quality": 0.9015}, DecisionOutcome.PASS, 0.9215)
    convergence_hash = convergence.convergence_hash or ""
    convergence_reason = (
        convergence.convergence_reason.value if convergence.convergence_reason else None
    )

    phase_agent = {
        PipelinePhase.PLAN: AgentType.PLANNER,
        PipelinePhase.EXECUTE: AgentType.READER,
        PipelinePhase.JUDGE: AgentType.JUDGE,
        PipelinePhase.VERIFY: AgentType.VERIFIER,
        PipelinePhase.FINALIZE: AgentType.ORCHESTRATOR,
    }

    phases = [
        phase
        for phase in definition.phases
        if phase not in (PipelinePhase.INIT, PipelinePhase.DONE)
    ]
    entries = []
    dry_run_model_metadata = {
        "provider": "dry-run",
        "model_name": "dry-run-model",
        "temperature": 0.0,
        "max_tokens": 512,
    }
    for idx, phase in enumerate(phases):
        start_time = base_time + timedelta(minutes=idx)
        end_time = start_time + timedelta(seconds=30)
        agent_type = phase_agent[phase]
        prompt_hash = hashlib.sha256(f"dry-run:{phase.value}".encode()).hexdigest()
        model_hash = hashlib.sha256(f"model:{phase.value}".encode()).hexdigest()
        output = {
            "text": f"{phase.value} result",
            "artifacts": {"phase": phase.value},
            "scores": {"quality": 0.8 + idx * 0.01},
            "confidence": round(0.8 + idx * 0.01, 3),
            "metadata": {
                "contract_version": CONTRACT_VERSION,
                "model_metadata": dry_run_model_metadata,
            },
            "decision": DecisionOutcome.PASS.value,
        }
        entry = {
            "agent_id": f"{agent_type.value}-agent",
            "node": phase.value.lower(),
            "status": "success",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "input": {"phase": phase.value, "agent_type": agent_type.value},
            "output": output,
            "error": None,
            "scores": {"quality": 0.8 + idx * 0.01},
            "prompt_hash": prompt_hash,
            "model_hash": model_hash,
            "phase": phase.value,
            "run_id": run_id,
            "stop_reason": None,
            "failure_artifact": None,
            "replay_metadata": {
                "input_hash": hashlib.sha256(
                    f"{run_id}:{phase.value}".encode()
                ).hexdigest(),
                "config_hash": config_hash,
                "model_id": f"dry-run:{phase.value}",
                "convergence_hash": convergence_hash,
                "contract_version": CONTRACT_VERSION,
                "model_metadata": dry_run_model_metadata,
            },
            "epistemic_status": None,
            "epistemic_verdict": None,
            "decision_artifact": None,
            "run_fingerprint": None,
            "termination_reason": None,
        }
        if phase == PipelinePhase.FINALIZE:
            entry["decision_artifact"] = DecisionArtifact(
                verdict=DecisionOutcome.PASS,
                justification="dry-run success",
                supporting_trace_ids=[run_id],
            ).model_dump()
            entry["epistemic_status"] = {
                "status": "certain",
                "justification": "dry-run",
            }
            entry["epistemic_verdict"] = EpistemicVerdict.CERTAIN.value
            entry["run_fingerprint"] = {
                "pipeline_definition": definition.to_payload(),
                "agent_contract_version": CONTRACT_VERSION,
                "config_snapshot": {"mode": "dry-run"},
                "fingerprint": hashlib.sha256(
                    json.dumps(
                        {
                            "definition": definition.to_payload(),
                            "contract_version": CONTRACT_VERSION,
                            "config": {"mode": "dry-run"},
                        },
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=False,
                    ).encode()
                ).hexdigest(),
            }
        entries.append(entry)

    expected = {
        "run_id": run_id,
        "started_at": base_time.isoformat(),
        "completed_at": (base_time + timedelta(minutes=4, seconds=30)).isoformat(),
        "status": "completed",
        "trace_schema_version": TRACE_SCHEMA_VERSION,
        "config_hash": config_hash,
        "pipeline_definition_hash": pipeline_hash,
        "agent_versions": {"pipeline": "dry-run"},
        "replay_status": "REPLAYABLE",
        "runtime_version": "dry-run",
        "convergence_hash": convergence_hash,
        "convergence_reason": convergence_reason,
        "model_metadata": dry_run_model_metadata,
        "termination_reason": "completed",
        "entries": entries,
    }

    trace = generate_dry_run_trace()
    assert trace.to_dict() == expected
