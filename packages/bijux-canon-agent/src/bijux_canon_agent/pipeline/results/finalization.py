"""Result helpers for pipeline executions."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, cast

from bijux_canon_agent.agents.critique import CritiqueAgent
from bijux_canon_agent.contracts.agent_contract import AgentOutputSchema
from bijux_canon_agent.pipeline.results.shard_merging import (
    apply_merge_errors,
    collect_stage_outputs,
    extend_stages_processed,
    initialize_merged_final_status,
    merge_stage_outputs,
    propagate_shard_status,
    update_critique_status,
)
from bijux_canon_agent.pipeline.results.types import (
    MergedShardResult,
    ShardResult,
)
from bijux_canon_agent.pipeline.termination import ExecutionTerminationReason


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
        merged_final_status = initialize_merged_final_status()
        errors: list[str] = []

        for stage in required_stages:
            stage_key = stage["name"]
            stage_outputs, stage_errors = collect_stage_outputs(
                stage_key, shard_results
            )
            errors.extend(stage_errors)

            if not stage_outputs:
                if errors:
                    merged_stages[stage_key] = {"error": "; ".join(errors)}
                apply_merge_errors(merged_final_status, errors)
                continue

            merged_stages[stage_key] = merge_stage_outputs(stage_key, stage_outputs)
            extend_stages_processed(
                merged_final_status,
                stage_key=stage_key,
                shard_count=len(shard_results),
            )

        critique_result = cast(Mapping[str, Any], merged_stages.get("critique", {}))
        update_critique_status(
            merged_final_status,
            critique_result,
            quality_threshold=self.quality_threshold,
            has_errors=bool(errors),
            shard_results=shard_results,
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

        propagate_shard_status(merged_final_status, shard_results)

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
