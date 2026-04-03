"""Support routines for the Bijux Agent CLI."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
import json
from pathlib import Path
import sys
import time
from typing import Any
import uuid

from bijux_canon_agent.interfaces.cli import result_artifacts as _result_artifacts_module
from bijux_canon_agent.interfaces.cli.config_support import (
    ensure_directory,
    load_config,
)
from bijux_canon_agent.interfaces.cli.result_artifacts import write_final_artifacts
from bijux_canon_agent.pipeline.canonical import AuditableDocPipeline
from bijux_canon_agent.pipeline.control.stop_conditions import StopReason
from bijux_canon_agent.pipeline.convergence.monitor import ConvergenceReason
from bijux_canon_agent.pipeline.epistemic import EpistemicVerdict
from bijux_canon_agent.replay import classify_replay_mismatch
from bijux_canon_agent.traces import (
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
from bijux_canon_agent.traces.trace import ModelMetadata

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


def build_trace_from_result(*args: Any, **kwargs: Any) -> tuple[Path, RunTrace]:
    """Build a run trace while preserving helper-level monkeypatch compatibility."""
    _result_artifacts_module.datetime = datetime
    _result_artifacts_module.uuid = uuid
    return _result_artifacts_module.build_trace_from_result(*args, **kwargs)


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
