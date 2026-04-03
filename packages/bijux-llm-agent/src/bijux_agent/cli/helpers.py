"""Support routines for the Bijux Agent CLI."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Any
import uuid

from bijux_agent.constants import AGENT_CONTRACT_VERSION
from bijux_agent.enums import DecisionOutcome
from bijux_agent.pipeline.canonical import AuditableDocPipeline
from bijux_agent.pipeline.control.phases import PipelinePhase
from bijux_agent.pipeline.control.stop_conditions import StopReason
from bijux_agent.pipeline.convergence.monitor import ConvergenceReason
from bijux_agent.pipeline.definition import standard_pipeline_definition
from bijux_agent.pipeline.epistemic import EpistemicVerdict
from bijux_agent.pipeline.results.outcome import PipelineResult
from bijux_agent.pipeline.termination import ExecutionTerminationReason
from bijux_agent.replay import classify_replay_mismatch
from bijux_agent.tracing import (
    EpistemicStatus,
    ReplayMetadata,
    ReplayStatus,
    RunFingerprint,
    RunTrace,
    RunTraceHeader,
    TraceEntry,
    upgrade_trace,
    validate_trace_payload,
)
from bijux_agent.tracing.trace import ModelMetadata
from bijux_agent.utilities import version
from bijux_agent.utilities.prompt_hash import prompt_hash
from bijux_agent.utilities.version import get_runtime_version


def ensure_directory(path: str) -> None:
    """Ensure the directory exists, creating it if necessary."""
    if path:
        dir_path = Path(path).resolve()
        dir_path.mkdir(parents=True, exist_ok=True)


def load_config(config_path: str, logger: Any) -> dict[str, Any]:
    """Load configuration from a YAML file."""
    try:
        import yaml
    except ImportError:
        logger.error(
            "PyYAML required to load config file. Install with: pip install pyyaml"
        )
        sys.exit(1)

    path = Path(config_path)
    if not path.exists():
        logger.warning(f"Config file not found at {config_path}, using defaults")
        return {}

    try:
        with open(path, encoding="utf-8") as file:
            config = yaml.safe_load(file)
        if not isinstance(config, dict):
            logger.error(f"Config file must contain a dictionary, got {type(config)}")
            sys.exit(1)
        return config
    except Exception as exc:
        logger.error(f"Failed to load config file {config_path}: {exc}")
        sys.exit(1)


async def process_files(
    pipeline: AuditableDocPipeline,
    files: list[Path],
    task_goal: str,
    logger: Any,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Process a list of files using the pipeline."""
    if not files:
        logger.warning("No files provided to process")
        return {
            "successful": [],
            "failed": [],
            "telemetry": {
                "total_files": 0,
                "successful": 0,
                "failed": 0,
                "duration_sec": 0,
            },
        }

    logger.info(f"Processing {len(files)} file(s)")
    start_time = time.time()
    results = {"successful": [], "failed": [], "telemetry": {}}

    for input_file in files:
        if not input_file.is_file():
            logger.error(f"Skipping invalid file path: {input_file}")
            results["failed"].append(
                {"file_path": str(input_file), "error": "Not a valid file"}
            )
            continue

        context = {
            "task_goal": task_goal,
            "file_path": str(input_file),
            "context_id": f"file_{input_file.stem}",
        }
        logger.info(f"Processing file: {input_file} with task goal: {task_goal}")

        if dry_run:
            logger.info(f"Dry run: Would process {input_file}")
            results["successful"].append(
                {
                    "file_path": str(input_file),
                    "status": "dry_run",
                    "message": "Dry run completed",
                }
            )
            continue

        try:
            result = await pipeline.run(context)
        except Exception as exc:
            logger.error(
                f"Unexpected error processing {input_file}: {exc}", exc_info=True
            )
            results["failed"].append({"file_path": str(input_file), "error": str(exc)})
            continue

        if "error" in result:
            logger.error(f"Pipeline failed for {input_file}: {result['error']}")
            results["failed"].append(
                {"file_path": str(input_file), "error": result["error"]}
            )
            continue

        results["successful"].append({"file_path": str(input_file), "result": result})

    duration = time.time() - start_time
    results["telemetry"] = {
        "total_files": len(files),
        "successful": len(results["successful"]),
        "failed": len(results["failed"]),
        "duration_sec": duration,
    }
    logger.info(f"Processing completed: {results['telemetry']}")
    return results


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


def _resolve_model_metadata(config: Mapping[str, Any]) -> ModelMetadata:
    raw = config.get("model_metadata")
    if raw is None:
        raise RuntimeError("model_metadata section missing from config")
    if not isinstance(raw, Mapping):
        raise RuntimeError("model_metadata must be an object")
    return ModelMetadata.from_mapping(raw)


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
        phase=PipelinePhase.FINALIZE.value,
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


def handle_replay(trace_path: Path) -> None:
    if not trace_path.exists():
        print(f"Trace not found: {trace_path}", file=sys.stderr)
        sys.exit(2)
    try:
        trace = load_trace(trace_path)
    except Exception as exc:
        print(f"Failed to load trace: {exc}", file=sys.stderr)
        sys.exit(1)
    result = PipelineResult.from_trace(trace)
    print("Reconstructed pipeline verdict:", result.decision.value)
    print("Confidence:", f"{result.confidence:.2f}")
    print("Stop reason:", result.stop_reason.value if result.stop_reason else "None")

    trace_parent = trace_path.parent
    results_root = trace_parent.parent if trace_parent.name == "trace" else trace_parent
    original_result_path = results_root / "result" / "final_result.json"
    if original_result_path.exists():
        original = json.loads(original_result_path.read_text(encoding="utf-8"))
        mismatches: list[str] = []
        if original.get("verdict") != result.decision.value:
            mismatches.append(
                f"verdict ({original.get('verdict')} != {result.decision.value})"
            )
        expected_confidence = float(original.get("confidence", 0.0))
        if abs(expected_confidence - result.confidence) > 1e-6:
            mismatches.append(
                f"confidence ({expected_confidence:.6f} != {result.confidence:.6f})"
            )
        expected_epistemic = original.get("epistemic_status")
        if expected_epistemic != result.epistemic_verdict.value:
            mismatches.append(
                f"epistemic_status ({expected_epistemic} != {result.epistemic_verdict.value})"
            )
        expected_stop_reason = original.get("stop_reason")
        actual_stop_reason = result.stop_reason.value if result.stop_reason else None
        if expected_stop_reason != actual_stop_reason:
            mismatches.append(
                f"stop_reason ({expected_stop_reason} != {actual_stop_reason})"
            )
        if mismatches:
            reason = classify_replay_mismatch(original, result)
            print(f"MISMATCH ({reason.value}):", "; ".join(mismatches))
        else:
            print("MATCH: trace matches final_result.json")
    else:
        print("Original final_result.json not found; comparison skipped.")


def load_trace(trace_path: Path) -> RunTrace:
    raw = json.loads(trace_path.read_text(encoding="utf-8"))
    upgraded = upgrade_trace(raw)
    validate_trace_payload(upgraded)
    raw = upgraded
    header_metadata = raw.get("model_metadata")
    header_model_metadata = (
        ModelMetadata.from_mapping(header_metadata)
        if isinstance(header_metadata, dict)
        else None
    )
    header = RunTraceHeader(
        trace_schema_version=raw.get("trace_schema_version", 1),
        config_hash=raw.get("config_hash", ""),
        pipeline_definition_hash=raw.get("pipeline_definition_hash", ""),
        agent_versions=raw.get("agent_versions", {}),
        replay_status=ReplayStatus(
            raw.get("replay_status", ReplayStatus.REPLAYABLE.value)
        ),
        runtime_version=raw.get("runtime_version", ""),
        convergence_hash=raw.get("convergence_hash", ""),
        convergence_reason=raw.get("convergence_reason"),
        model_metadata=header_model_metadata,
    )
    entries = [
        TraceEntry(
            agent_id=raw_entry["agent_id"],
            node=raw_entry["node"],
            status=raw_entry["status"],
            start_time=datetime.fromisoformat(raw_entry["start_time"]),
            end_time=datetime.fromisoformat(raw_entry["end_time"]),
            input=raw_entry.get("input", {}),
            output=raw_entry.get("output"),
            error=raw_entry.get("error"),
            scores=raw_entry.get("scores", {}),
            prompt_hash=raw_entry.get("prompt_hash", ""),
            model_hash=raw_entry.get("model_hash", ""),
            phase=raw_entry.get("phase"),
            run_id=raw_entry.get("run_id"),
            stop_reason=StopReason(raw_entry["stop_reason"])
            if raw_entry.get("stop_reason")
            else None,
            failure_artifact=None,
            replay_metadata=_load_replay_metadata(raw_entry.get("replay_metadata", {})),
            epistemic_status=EpistemicStatus(**raw_entry["epistemic_status"])
            if raw_entry.get("epistemic_status")
            else None,
            epistemic_verdict=EpistemicVerdict(raw_entry["epistemic_verdict"])
            if raw_entry.get("epistemic_verdict")
            else None,
            decision_artifact=None,
            run_fingerprint=None,
        )
        for raw_entry in raw["entries"]
    ]
    return RunTrace(
        run_id=raw.get("run_id", "unknown"),
        started_at=datetime.fromisoformat(raw["started_at"]),
        completed_at=datetime.fromisoformat(raw["completed_at"])
        if raw.get("completed_at")
        else None,
        status=raw.get("status", "completed"),
        header=header,
        entries=entries,
    )


def _load_replay_metadata(raw_metadata: Mapping[str, Any] | None) -> ReplayMetadata:
    raw_metadata = raw_metadata or {}
    payload = dict(raw_metadata)
    raw_model_metadata = payload.get("model_metadata")
    if raw_model_metadata and isinstance(raw_model_metadata, Mapping):
        payload["model_metadata"] = ModelMetadata.from_mapping(raw_model_metadata)
    return ReplayMetadata(**payload)
