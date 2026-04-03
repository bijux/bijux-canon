"""Ensure execution-plan resolution stays consistent with its helpers."""

from __future__ import annotations

from dataclasses import dataclass

from bijux_canon_agent.pipeline.agent_registry import determine_execution_plan
from bijux_canon_agent.pipeline.execution_plan import (
    build_execution_plan,
    filter_execution_plan_for_goal,
)


@dataclass
class _DummyPipeline:
    stage_timeout: float = 1.0
    file_reader: object = object()
    summarizer: object = object()
    validator: object = object()
    critique: object = object()


def test_execution_plan_matches_filter() -> None:
    pipeline = _DummyPipeline()
    definitions = build_execution_plan(pipeline)
    filtered = filter_execution_plan_for_goal("summarize this doc", definitions)
    resolved = determine_execution_plan(pipeline, "summarize this doc")
    assert [stage["name"] for stage in resolved] == [
        stage["name"] for stage in filtered
    ]
