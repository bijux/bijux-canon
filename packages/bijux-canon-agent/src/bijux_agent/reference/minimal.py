"""Minimal reference pipeline with explicit defaults."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from bijux_agent.config.defaults import MINIMAL_REFERENCE_CONFIG
from bijux_agent.pipeline.canonical import AuditableDocPipeline
from bijux_agent.utilities.logger_manager import LoggerConfig, LoggerManager


@dataclass(frozen=True)
class MinimalPipeline:
    """Thin wrapper around the canonical pipeline with explicit defaults."""

    pipeline: AuditableDocPipeline
    logger_manager: LoggerManager


def build_minimal_pipeline(
    *,
    config: dict[str, Any] | None = None,
    logger_manager: LoggerManager | None = None,
) -> MinimalPipeline:
    resolved_config = dict(MINIMAL_REFERENCE_CONFIG)
    if config:
        resolved_config.update(config)
    logger = logger_manager or LoggerManager(LoggerConfig())
    pipeline = AuditableDocPipeline(resolved_config, logger)
    return MinimalPipeline(pipeline=pipeline, logger_manager=logger)


async def run_minimal(
    *,
    text: str,
    task_goal: str,
    context_id: str = "minimal",
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the minimal pipeline against inline text."""
    wrapper = build_minimal_pipeline(config=config)
    return await wrapper.pipeline.run(
        {
            "context_id": context_id,
            "text": text,
            "task_goal": task_goal,
        }
    )
