"""Serialization helpers for trace models."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any


def serialize_value(value: Any) -> Any:
    """Ensure model-like values become JSON-serializable structures."""
    dumper = getattr(value, "model_dump", None)
    if callable(dumper):
        return dumper()
    dumper = getattr(value, "dict", None)
    if callable(dumper):
        return dumper()
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    return value


def serialize_trace_entry(entry: Any) -> dict[str, Any]:
    """Serialize a TraceEntry-like object into a dictionary."""
    failure_dict = None
    if entry.failure_artifact:
        failure_dict = serialize_value(entry.failure_artifact)
        failure_dict["phase"] = entry.failure_artifact.phase.value
    output_value = None
    if entry.output is not None:
        output_value = serialize_value(entry.output)
    return {
        "agent_id": entry.agent_id,
        "node": entry.node,
        "status": entry.status,
        "start_time": entry.start_time.isoformat(),
        "end_time": entry.end_time.isoformat(),
        "input": entry.input,
        "output": output_value,
        "error": entry.error,
        "scores": entry.scores,
        "prompt_hash": entry.prompt_hash,
        "model_hash": entry.model_hash,
        "phase": entry.phase,
        "run_id": entry.run_id,
        "stop_reason": entry.stop_reason.value if entry.stop_reason else None,
        "failure_artifact": failure_dict,
        "replay_metadata": asdict(entry.replay_metadata),
        "epistemic_status": asdict(entry.epistemic_status)
        if entry.epistemic_status
        else None,
        "epistemic_verdict": entry.epistemic_verdict.value
        if entry.epistemic_verdict
        else None,
        "decision_artifact": serialize_value(entry.decision_artifact)
        if entry.decision_artifact
        else None,
        "run_fingerprint": asdict(entry.run_fingerprint)
        if entry.run_fingerprint
        else None,
        "termination_reason": entry.termination_reason.value
        if entry.termination_reason
        else None,
    }


def serialize_run_trace(trace: Any) -> dict[str, Any]:
    """Serialize a RunTrace-like object into a dictionary."""
    return {
        "run_id": trace.run_id,
        "started_at": trace.started_at.isoformat(),
        "completed_at": trace.completed_at.isoformat() if trace.completed_at else None,
        "status": trace.status,
        "trace_schema_version": trace.header.trace_schema_version,
        "config_hash": trace.header.config_hash,
        "pipeline_definition_hash": trace.header.pipeline_definition_hash,
        "agent_versions": trace.header.agent_versions,
        "replay_status": trace.header.replay_status.value,
        "runtime_version": trace.header.runtime_version,
        "convergence_hash": trace.header.convergence_hash,
        "convergence_reason": trace.header.convergence_reason,
        "termination_reason": trace.header.termination_reason.value
        if trace.header.termination_reason
        else None,
        "model_metadata": asdict(trace.header.model_metadata)
        if trace.header.model_metadata
        else None,
        "entries": [serialize_trace_entry(entry) for entry in trace.entries],
    }
