"""Final artifact and trace writing helpers for the Bijux Agent CLI."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import uuid
from typing import Any

from bijux_canon_agent.constants import AGENT_CONTRACT_VERSION
from bijux_canon_agent.core import version
from bijux_canon_agent.core.hashing import prompt_hash
from bijux_canon_agent.core.version import get_runtime_version
from bijux_canon_agent.enums import DecisionOutcome
from bijux_canon_agent.pipeline.canonical import AuditableDocPipeline
from bijux_canon_agent.pipeline.control.lifecycle import PipelineLifecycle
from bijux_canon_agent.pipeline.convergence.monitor import ConvergenceReason
from bijux_canon_agent.pipeline.definition import standard_pipeline_definition
from bijux_canon_agent.pipeline.epistemic import EpistemicVerdict
from bijux_canon_agent.pipeline.results.outcome import PipelineResult
from bijux_canon_agent.pipeline.termination import ExecutionTerminationReason
from bijux_canon_agent.traces import (
    ReplayMetadata,
    RunFingerprint,
    RunTrace,
    RunTraceHeader,
    TraceEntry,
)
from bijux_canon_agent.traces.trace import ModelMetadata


def write_final_artifacts(
    *,
    success_entry: dict[str, Any] | None,
    results: dict[str, Any],
    config: Mapping[str, Any],
    task_goal: str,
    results_dir: Path,
    dry_run: bool,
    convergence_hash: str | None = None,
    convergence_reason: ConvergenceReason | None = None,
) -> Path:
    """Write final result and trace artifacts for a completed pipeline run."""
    result_dir = results_dir / "result"
    trace_dir = results_dir / "trace"
    result_dir.mkdir(parents=True, exist_ok=True)
    trace_dir.mkdir(parents=True, exist_ok=True)
    final_result_path = result_dir / "final_result.json"
    pipeline_result = success_entry["result"] if success_entry else None
    if pipeline_result and not dry_run:
        final_status = pipeline_result["final_status"]
        success_flag = bool(final_status.get("success"))
        termination_reason = final_status.get(
            "termination_reason", ExecutionTerminationReason.COMPLETED
        )
        trace_path, trace = build_trace_from_result(
            pipeline_result=pipeline_result,
            file_path=success_entry["file_path"],
            task_goal=task_goal,
            config=config,
            verdict=DecisionOutcome.PASS if success_flag else DecisionOutcome.VETO,
            confidence=float(final_status.get("score", 0.0)),
            trace_dir=trace_dir,
            convergence_hash=convergence_hash,
            convergence_reason=convergence_reason,
            termination_reason=termination_reason,
        )
        pipeline_result_from_trace = PipelineResult.from_trace(trace)
        trace_relative = str(trace_path.relative_to(results_dir))
    else:
        pipeline_result_from_trace = None
        trace_relative = None

    runtime_version = (
        trace.header.runtime_version
        if pipeline_result_from_trace
        else get_runtime_version()
    )
    if pipeline_result_from_trace:
        term_reason_payload = (
            termination_reason.value
            if isinstance(termination_reason, ExecutionTerminationReason)
            else termination_reason
        )
        convergence_flag = bool(final_status.get("converged"))
        convergence_reason_payload = final_status.get("convergence_reason")
        convergence_iterations_payload = final_status.get("convergence_iterations", 0)
        payload = {
            "verdict": pipeline_result_from_trace.decision.value,
            "confidence": pipeline_result_from_trace.confidence,
            "epistemic_status": pipeline_result_from_trace.epistemic_verdict.value,
            "stop_reason": pipeline_result_from_trace.stop_reason.value
            if pipeline_result_from_trace.stop_reason
            else None,
            "trace_path": trace_relative,
            "runtime_version": runtime_version,
            "termination_reason": term_reason_payload,
            "converged": convergence_flag,
            "convergence_reason": convergence_reason_payload,
            "convergence_iterations": convergence_iterations_payload,
            "model_metadata": asdict(pipeline_result_from_trace.model_metadata),
        }
    else:
        payload = {
            "verdict": DecisionOutcome.VETO.value,
            "confidence": 0.0,
            "epistemic_status": EpistemicVerdict.CERTAIN.value,
            "stop_reason": None,
            "trace_path": None,
            "runtime_version": runtime_version,
            "termination_reason": ExecutionTerminationReason.COMPLETED.value,
            "converged": False,
            "convergence_reason": None,
            "convergence_iterations": 0,
        }

    final_result_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return final_result_path


def build_trace_from_result(
    *,
    pipeline_result: dict[str, Any],
    file_path: str,
    task_goal: str,
    config: Mapping[str, Any],
    verdict: DecisionOutcome,
    confidence: float,
    trace_dir: Path,
    convergence_hash: str | None = None,
    convergence_reason: ConvergenceReason | str | None = None,
    termination_reason: ExecutionTerminationReason | str | None = None,
) -> tuple[Path, RunTrace]:
    """Build and write a run trace from a pipeline result payload."""
    trace_dir.mkdir(parents=True, exist_ok=True)
    run_id = f"run-{uuid.uuid4().hex}"
    start_time = datetime.now(UTC)
    status = (
        "completed" if pipeline_result["final_status"].get("success") else "aborted"
    )
    config_payload = json.dumps(config or {}, sort_keys=True)
    config_hash = hashlib.sha256(config_payload.encode()).hexdigest()
    definition_payload = standard_pipeline_definition().to_payload()
    definition_hash = hashlib.sha256(
        json.dumps(definition_payload, sort_keys=True).encode()
    ).hexdigest()
    fingerprint = RunFingerprint.create(
        definition=standard_pipeline_definition(),
        config=config or {},
    )
    model_metadata = _resolve_model_metadata(config)
    prompt_seed = f"{task_goal}:{file_path}"
    entry_prompt_hash = prompt_hash(prompt_seed)
    model_hash_value = hashlib.sha256(AuditableDocPipeline.NAME.encode()).hexdigest()
    convergence_reason_value: str | None = None
    if isinstance(convergence_reason, ConvergenceReason):
        convergence_reason_value = convergence_reason.value
    elif isinstance(convergence_reason, str):
        convergence_reason_value = convergence_reason
    termination_reason_enum = ExecutionTerminationReason.COMPLETED
    if isinstance(termination_reason, ExecutionTerminationReason):
        termination_reason_enum = termination_reason
    elif isinstance(termination_reason, str):
        try:
            termination_reason_enum = ExecutionTerminationReason(termination_reason)
        except ValueError:
            termination_reason_enum = ExecutionTerminationReason.COMPLETED
    header = RunTraceHeader(
        config_hash=config_hash,
        pipeline_definition_hash=definition_hash,
        agent_versions={"pipeline": AuditableDocPipeline.NAME},
        runtime_version=version.get_runtime_version(),
        convergence_hash=convergence_hash or "",
        convergence_reason=convergence_reason_value,
        termination_reason=termination_reason_enum,
        model_metadata=model_metadata,
    )
    entry = TraceEntry(
        agent_id=AuditableDocPipeline.NAME,
        node="finalize",
        status="success"
        if pipeline_result["final_status"].get("success")
        else "failed",
        start_time=start_time,
        end_time=start_time,
        input={"task_goal": task_goal, "file_path": file_path},
        output={
            "text": pipeline_result.get("result", {}),
            "artifacts": pipeline_result.get("stages", {}),
            "scores": {"quality": confidence},
            "confidence": confidence,
            "metadata": {
                "contract_version": AGENT_CONTRACT_VERSION,
                "model_metadata": asdict(model_metadata),
            },
            "decision": verdict.value,
        },
        scores={"quality": confidence},
        prompt_hash=entry_prompt_hash,
        model_hash=model_hash_value,
        phase=PipelineLifecycle.FINALIZE.value,
        run_id=run_id,
        stop_reason=None,
        failure_artifact=None,
        replay_metadata=ReplayMetadata(
            input_hash=hashlib.sha256(f"{file_path}:{task_goal}".encode()).hexdigest(),
            config_hash=config_hash,
            model_id=AuditableDocPipeline.NAME,
            convergence_hash=convergence_hash or "",
            model_metadata=model_metadata,
        ),
        epistemic_status=None,
        epistemic_verdict=EpistemicVerdict.CERTAIN,
        decision_artifact=None,
        run_fingerprint=fingerprint,
        termination_reason=termination_reason_enum,
    )
    trace = RunTrace(
        run_id=run_id,
        started_at=start_time,
        completed_at=start_time,
        status=status,
        header=header,
        entries=[entry],
    )
    trace_path = trace_dir / "run_trace.json"
    trace_path.write_text(json.dumps(trace.to_dict(), indent=2), encoding="utf-8")
    return trace_path, trace


def _resolve_model_metadata(config: Mapping[str, Any]) -> ModelMetadata:
    raw = config.get("model_metadata")
    if raw is None:
        raise RuntimeError("model_metadata section missing from config")
    if not isinstance(raw, Mapping):
        raise RuntimeError("model_metadata must be an object")
    return ModelMetadata.from_mapping(raw)


__all__ = ["build_trace_from_result", "write_final_artifacts"]
