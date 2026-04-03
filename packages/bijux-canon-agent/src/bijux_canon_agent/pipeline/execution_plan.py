"""Execution-plan helpers for composing pipeline runs."""

from __future__ import annotations

from collections.abc import Sequence
import time
from typing import Any


def build_execution_plan(pipeline: Any) -> list[dict[str, Any]]:
    """Return the base execution plan for the pipeline run."""

    return [
        {
            "name": "file_extraction",
            "agent": pipeline.file_reader,
            "weight": 1.0,
            "dependencies": [],
            "condition": lambda ctx: "file_path" in ctx,
            "timeout": pipeline.stage_timeout,
            "output_key": "file_extraction",
        },
        {
            "name": "summarization",
            "agent": pipeline.summarizer,
            "dependencies": ["file_extraction"],
            "condition": lambda ctx: (
                "file_extraction" in ctx
                and isinstance(ctx["file_extraction"], dict)
                and "text" in ctx["file_extraction"]
                and isinstance(ctx["file_extraction"]["text"], str)
                and ctx["file_extraction"]["text"].strip()
            ),
            "timeout": pipeline.stage_timeout,
            "output_key": "summarization",
        },
        {
            "name": "validation",
            "agent": pipeline.validator,
            "dependencies": ["summarization"],
            "condition": lambda ctx: (
                "summarization" in ctx
                and isinstance(ctx["summarization"], dict)
                and "summary" in ctx["summarization"]
                and isinstance(ctx["summarization"]["summary"], dict)
            ),
            "timeout": pipeline.stage_timeout,
            "output_key": "validation_result",
        },
        {
            "name": "critique",
            "agent": pipeline.critique,
            "dependencies": ["summarization", "validation"],
            "condition": lambda ctx: (
                "summarization" in ctx
                and isinstance(ctx["summarization"], dict)
                and "summary" in ctx["summarization"]
                and isinstance(ctx["summarization"]["summary"], dict)
            ),
            "timeout": pipeline.stage_timeout,
            "output_key": "critique_result",
        },
    ]


def filter_execution_plan_for_goal(
    task_goal: str,
    definitions: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return the subset of execution steps relevant to a task goal."""

    task_goal = task_goal.lower()
    if "summarize" in task_goal:
        targets = {"file_extraction", "summarization", "validation", "critique"}
    elif "answer" in task_goal:
        targets = {"file_extraction", "summarization", "critique"}
    else:
        targets = {step["name"] for step in definitions}

    return [step for step in definitions if step["name"] in targets]


def merge_summary_outputs(step_outputs: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Construct the merged summary output from multiple shards."""

    executive_summaries = []
    key_points: list[Any] = []
    actionable_insights = []
    critical_risks = []
    missing_info = []
    for output in step_outputs:
        summary = output.get("summary", {})
        executive_summaries.append(summary.get("executive_summary", ""))
        key_points.extend(summary.get("key_points", []))
        actionable_insights.append(summary.get("actionable_insights", ""))
        critical_risks.append(summary.get("critical_risks", ""))
        missing_info.append(summary.get("missing_info", ""))

    merged_summary = {
        "summary": {
            "executive_summary": " ".join(s for s in executive_summaries if s),
            "key_points": list(dict.fromkeys(key_points)),
            "actionable_insights": (
                " ".join(s for s in actionable_insights if s)
                or "No actionable insights available"
            ),
            "critical_risks": (
                " ".join(s for s in critical_risks if s)
                or "No critical risks identified"
            ),
            "missing_info": (
                " ".join(s for s in missing_info if s) or "No missing information noted"
            ),
        },
        "method": step_outputs[0].get("method", "unknown")
        if step_outputs
        else "unknown",
        "input_length": sum(output.get("input_length", 0) for output in step_outputs),
        "backend": step_outputs[0].get("backend", "unknown")
        if step_outputs
        else "unknown",
        "strategy": step_outputs[0].get("strategy", "unknown")
        if step_outputs
        else "unknown",
        "audit": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "shards_merged": len(step_outputs),
        },
    }
    return merged_summary
