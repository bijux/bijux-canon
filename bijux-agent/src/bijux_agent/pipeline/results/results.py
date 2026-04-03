"""Result helpers for pipeline executions."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import time
from typing import Any, cast

from bijux_agent.agents.critique import CritiqueAgent
from bijux_agent.models.contract import AgentOutputSchema
from bijux_agent.pipeline.results.types import (
    FinalStatus,
    MergedShardResult,
    ShardResult,
)
from bijux_agent.pipeline.stages import build_summary_stage
from bijux_agent.pipeline.termination import ExecutionTerminationReason


class PipelineResultsMixin:
    """Mix-in encapsulating result handling helpers."""

    logger: Any
    logger_manager: Any
    quality_threshold: float
    critique: CritiqueAgent
    _metric_type: Any

    async def _merge_shard_results(
        self,
        shard_results: Sequence[ShardResult],
        required_stages: Sequence[Mapping[str, Any]],
    ) -> MergedShardResult:
        if not shard_results:
            return {
                "stages": {},
                "final_status": {
                    "success": False,
                    "error": "No shard results to merge",
                    "stages_processed": [],
                    "iterations": 0,
                    "termination_reason": ExecutionTerminationReason.FAILURE,
                },
            }

        merged_stages: dict[str, dict[str, Any]] = {}
        merged_final_status: FinalStatus = {
            "success": True,
            "stages_processed": [],
            "iterations": 0,
            "termination_reason": ExecutionTerminationReason.COMPLETED,
            "converged": False,
            "convergence_reason": None,
            "convergence_iterations": 0,
        }
        errors: list[str] = []

        for stage in required_stages:
            stage_key = stage["name"]
            stage_outputs_with_index: list[tuple[int, dict[str, Any]]] = []
            for shard_idx, shard_result in enumerate(shard_results):
                stage_output = shard_result["stages"].get(stage_key, {})
                if "error" in stage_output:
                    errors.append(
                        f"Shard failed in stage {stage_key}: {stage_output['error']}"
                    )
                    continue
                stage_outputs_with_index.append((shard_idx, stage_output))

            if not stage_outputs_with_index:
                if errors:
                    merged_stages[stage_key] = {"error": "; ".join(errors)}
                merged_final_status["success"] = False
                merged_final_status["error"] = "; ".join(errors)
                merged_final_status["termination_reason"] = (
                    ExecutionTerminationReason.FAILURE
                )
                continue

            stage_outputs = [
                output
                for _, output in sorted(
                    stage_outputs_with_index, key=lambda pair: pair[0]
                )
            ]

            if stage_key == "file_extraction":
                merged_text = "\n\n".join(
                    output.get("text", "") for output in stage_outputs
                )
                merged_stages[stage_key] = {
                    "text": merged_text,
                    "input_length": sum(
                        output.get("input_length", 0) for output in stage_outputs
                    ),
                    "audit": {
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "shards_merged": len(stage_outputs),
                    },
                }
            elif stage_key == "summarization":
                merged_stages[stage_key] = build_summary_stage(stage_outputs)
            else:
                merged_stages[stage_key] = stage_outputs[-1]
                audit_info = {
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "shards_merged": len(stage_outputs),
                }
                merged_stages[stage_key]["audit"] = audit_info

            merged_final_status["stages_processed"].extend(
                [f"{stage_key}_shard_{i}" for i in range(len(shard_results))]
            )

        critique_result = cast(Mapping[str, Any], merged_stages.get("critique", {}))
        critique_status = str(critique_result.get("critique_status", "unknown"))
        critique_score = float(critique_result.get("score", 0.0))
        merged_final_status["success"] = (
            critique_status != "needs_revision"
            and critique_score >= self.quality_threshold
            and not errors
        )
        merged_final_status["score"] = critique_score
        merged_final_status["critique_status"] = critique_status
        merged_final_status["iterations"] = max(
            shard["final_status"]["iterations"] for shard in shard_results
        )

        self.logger.info(
            "Merged shard results",
            extra={
                "context": {
                    "merged_stages": list(merged_stages.keys()),
                    "errors": errors,
                    "stage": "merge_shards",
                }
            },
        )

        # Propagate execution metadata from shards when non-complete reasons are present
        for shard in shard_results:
            shard_status = shard["final_status"]
            reason = shard_status.get(
                "termination_reason", ExecutionTerminationReason.COMPLETED
            )
            if (
                reason != ExecutionTerminationReason.COMPLETED
                and merged_final_status["termination_reason"]
                == ExecutionTerminationReason.COMPLETED
            ):
                merged_final_status["termination_reason"] = reason
            if shard_status.get("converged"):
                merged_final_status["converged"] = True
                if not merged_final_status.get("convergence_reason"):
                    merged_final_status["convergence_reason"] = shard_status.get(
                        "convergence_reason"
                    )
            merged_final_status["convergence_iterations"] = max(
                merged_final_status.get("convergence_iterations", 0),
                shard_status.get("convergence_iterations", 0),
            )
            if shard_status.get("error") and not merged_final_status.get("error"):
                merged_final_status["error"] = shard_status["error"]

        return {"stages": merged_stages, "final_status": merged_final_status}

    async def _extract_final_result(
        self, stages: dict[str, dict[str, Any]], task_goal: str
    ) -> Any:
        task_goal = task_goal.lower()
        if "summarize" in task_goal:
            return stages.get("summarization", {}).get("summary", {})
        if "answer" in task_goal:
            return (
                stages.get("summarization", {})
                .get("summary", {})
                .get("executive_summary", "No answer generated")
            )
        last_stage = list(stages.keys())[-1] if stages else None
        return stages.get(last_stage, {}) if last_stage else {}

    async def _validate_final_result(
        self, result: Any, task_goal: str, context_id: str | None = None
    ) -> dict[str, Any]:
        critique_agent = self.critique
        if critique_agent is None:
            return {"is_valid": True, "issues": []}

        critique_context: dict[str, Any] = {
            "task_goal": task_goal,
            "result": result,
        }
        if context_id is not None:
            critique_context["context_id"] = context_id
        critique_result = await critique_agent.run(critique_context)
        if isinstance(critique_result, AgentOutputSchema):
            metadata = critique_result.metadata
            critique_status = metadata.get("critique_status", "unknown")
            critique_score = metadata.get("score", critique_result.confidence)
            per_criterion = metadata.get("per_criterion", [])
        else:
            critique_status = critique_result["critique_status"]
            critique_score = critique_result["score"]
            per_criterion = critique_result["per_criterion"]
        is_valid = critique_status == "ok" and critique_score >= self.quality_threshold
        return {"is_valid": is_valid, "issues": per_criterion}

    async def _apply_feedback_rules(
        self,
        stage_name: str,
        stage_result: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        rules = getattr(self, "feedback_rules", {})
        stage_rules = rules.get(stage_name, {})
        if not stage_rules:
            return {"retry": False}

        if stage_name == "critique":
            critique_status = stage_result.get("critique_status", "unknown")
            score = stage_result.get("score", 0.0)
            if critique_status == "needs_revision" or score < self.quality_threshold:
                critical_issues = [
                    c
                    for c in stage_result.get("per_criterion", [])
                    if c.get("severity") == "Critical"
                ]
                major_issues = [
                    c
                    for c in stage_result.get("per_criterion", [])
                    if c.get("severity") == "Major"
                ]
                minor_issues = [
                    c
                    for c in stage_result.get("per_criterion", [])
                    if c.get("severity") == "Minor"
                ]
                issues = critical_issues + major_issues + minor_issues

                feedback_score = (
                    len(critical_issues) * 1.0
                    + len(major_issues) * 0.5
                    + len(minor_issues) * 0.1
                )
                retry_threshold = stage_rules.get("retry_threshold", 0.5)

                if issues and feedback_score >= retry_threshold:
                    suggestions = [
                        c["suggestion"] for c in issues if c.get("suggestion")
                    ]
                    self.logger_manager.log_metric(
                        "feedback_score",
                        feedback_score,
                        self._metric_type.GAUGE,
                        tags={"stage": stage_name},
                    )
                    return {
                        "retry": True,
                        "reason": (
                            f"Feedback score {feedback_score:.2f} exceeds "
                            f"threshold {retry_threshold}: "
                            f"{[c['issues'] for c in issues]}"
                        ),
                        "updated_context": {
                            **context,
                            "feedback": (
                                f"Revise to address: {suggestions}"
                                if suggestions
                                else "Revise based on critique feedback"
                            ),
                        },
                        "feedback_score": feedback_score,
                    }
        elif (
            stage_name == "summarization"
            and stage_result.get("summary", {}).get("executive_summary", "").strip()
            == ""
        ):
            return {
                "retry": True,
                "reason": "Empty summary produced",
                "updated_context": {
                    **context,
                    "feedback": "Generate a non-empty summary",
                },
                "feedback_score": 1.0,
            }
        return {"retry": False}
