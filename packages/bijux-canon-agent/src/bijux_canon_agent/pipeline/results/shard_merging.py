"""Shard-merging helpers for pipeline result finalization."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import time
from typing import Any

from bijux_canon_agent.pipeline.results.summary import merge_summary_outputs
from bijux_canon_agent.pipeline.results.types import FinalStatus, ShardResult
from bijux_canon_agent.pipeline.termination import ExecutionTerminationReason


def initialize_merged_final_status() -> FinalStatus:
    """Create the default final-status payload for merged shards."""
    return {
        "success": True,
        "stages_processed": [],
        "iterations": 0,
        "termination_reason": ExecutionTerminationReason.COMPLETED,
        "converged": False,
        "convergence_reason": None,
        "convergence_iterations": 0,
    }


def collect_stage_outputs(
    stage_key: str,
    shard_results: Sequence[ShardResult],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Collect successful stage outputs and stage errors across shards."""
    outputs_with_index: list[tuple[int, dict[str, Any]]] = []
    errors: list[str] = []
    for shard_idx, shard_result in enumerate(shard_results):
        stage_output = shard_result["stages"].get(stage_key, {})
        if "error" in stage_output:
            errors.append(f"Shard failed in stage {stage_key}: {stage_output['error']}")
            continue
        outputs_with_index.append((shard_idx, stage_output))
    outputs = [
        output for _, output in sorted(outputs_with_index, key=lambda pair: pair[0])
    ]
    return outputs, errors


def merge_stage_outputs(
    stage_key: str,
    stage_outputs: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """Merge successful outputs for a specific pipeline stage."""
    if stage_key == "file_extraction":
        return {
            "text": "\n\n".join(output.get("text", "") for output in stage_outputs),
            "input_length": sum(
                output.get("input_length", 0) for output in stage_outputs
            ),
            "audit": build_merge_audit(len(stage_outputs)),
        }
    if stage_key == "summarization":
        return merge_summary_outputs(stage_outputs)
    merged_output = dict(stage_outputs[-1])
    merged_output["audit"] = build_merge_audit(len(stage_outputs))
    return merged_output


def build_merge_audit(shards_merged: int) -> dict[str, Any]:
    """Return audit metadata for a merged stage."""
    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "shards_merged": shards_merged,
    }


def extend_stages_processed(
    final_status: FinalStatus,
    *,
    stage_key: str,
    shard_count: int,
) -> None:
    """Record merged shard identifiers for a stage."""
    final_status["stages_processed"].extend(
        [f"{stage_key}_shard_{i}" for i in range(shard_count)]
    )


def apply_merge_errors(
    final_status: FinalStatus,
    errors: Sequence[str],
) -> None:
    """Mark the final status failed when merge errors are present."""
    if not errors:
        return
    final_status["success"] = False
    final_status["error"] = "; ".join(errors)
    final_status["termination_reason"] = ExecutionTerminationReason.FAILURE


def propagate_shard_status(
    final_status: FinalStatus,
    shard_results: Sequence[ShardResult],
) -> None:
    """Propagate termination and convergence metadata from shard statuses."""
    for shard in shard_results:
        shard_status = shard["final_status"]
        reason = shard_status.get(
            "termination_reason", ExecutionTerminationReason.COMPLETED
        )
        if (
            reason != ExecutionTerminationReason.COMPLETED
            and final_status["termination_reason"]
            == ExecutionTerminationReason.COMPLETED
        ):
            final_status["termination_reason"] = reason
        if shard_status.get("converged"):
            final_status["converged"] = True
            if not final_status.get("convergence_reason"):
                final_status["convergence_reason"] = shard_status.get(
                    "convergence_reason"
                )
        final_status["convergence_iterations"] = max(
            final_status.get("convergence_iterations", 0),
            shard_status.get("convergence_iterations", 0),
        )
        if shard_status.get("error") and not final_status.get("error"):
            final_status["error"] = shard_status["error"]


def update_critique_status(
    final_status: FinalStatus,
    critique_result: Mapping[str, Any],
    *,
    quality_threshold: float,
    has_errors: bool,
    shard_results: Sequence[ShardResult],
) -> None:
    """Apply critique-derived final-status fields after shard merging."""
    critique_status = str(critique_result.get("critique_status", "unknown"))
    critique_score = float(critique_result.get("score", 0.0))
    final_status["success"] = (
        critique_status != "needs_revision"
        and critique_score >= quality_threshold
        and not has_errors
    )
    final_status["score"] = critique_score
    final_status["critique_status"] = critique_status
    final_status["iterations"] = max(
        shard["final_status"]["iterations"] for shard in shard_results
    )
