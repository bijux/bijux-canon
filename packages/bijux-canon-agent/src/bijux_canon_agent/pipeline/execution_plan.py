"""Execution-plan helpers for composing pipeline runs."""

from __future__ import annotations

from collections.abc import Sequence
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
