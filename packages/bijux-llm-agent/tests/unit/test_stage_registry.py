"""Ensure stage resolution stays consistent with its helpers."""

from __future__ import annotations

from dataclasses import dataclass

from bijux_agent.pipeline.agent_registry import determine_required_stages
from bijux_agent.pipeline.stages import (
    build_stage_definitions,
    filter_stages_for_goal,
)


@dataclass
class _DummyPipeline:
    stage_timeout: float = 1.0
    file_reader: object = object()
    summarizer: object = object()
    validator: object = object()
    critique: object = object()


def test_stage_registry_matches_filter() -> None:
    pipeline = _DummyPipeline()
    definitions = build_stage_definitions(pipeline)
    filtered = filter_stages_for_goal("summarize this doc", pipeline, definitions)
    resolved = determine_required_stages(pipeline, "summarize this doc")
    assert [stage["name"] for stage in resolved] == [
        stage["name"] for stage in filtered
    ]
