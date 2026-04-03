"""Reference pipeline for document review workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from bijux_agent.pipeline.canonical import AuditableDocPipeline
from bijux_agent.utilities.logger_manager import LoggerConfig, LoggerManager

DOCUMENT_REVIEW_CONFIG: dict[str, Any] = {
    "pipeline": {"parameters": {"stage_timeout": 20}},
    "agents": ["file_reader", "summarizer", "critique", "validator"],
}


@dataclass(frozen=True)
class DocumentReviewPipeline:
    """Explicit, no-magic configuration for document review runs."""

    pipeline: AuditableDocPipeline
    logger_manager: LoggerManager


def build_document_review_pipeline(
    *,
    config: dict[str, Any] | None = None,
    logger_manager: LoggerManager | None = None,
) -> DocumentReviewPipeline:
    resolved_config = dict(DOCUMENT_REVIEW_CONFIG)
    if config:
        resolved_config.update(config)
    logger = logger_manager or LoggerManager(LoggerConfig())
    pipeline = AuditableDocPipeline(resolved_config, logger)
    return DocumentReviewPipeline(pipeline=pipeline, logger_manager=logger)


async def run_document_review(
    *,
    file_path: str,
    task_goal: str,
    context_id: str = "document-review",
    config: dict[str, Any] | None = None,
    reviewer_notes: str | None = None,
) -> dict[str, Any]:
    """Run the document review pipeline against a file path."""
    wrapper = build_document_review_pipeline(config=config)
    context = {
        "context_id": context_id,
        "file_path": file_path,
        "task_goal": task_goal,
    }
    if reviewer_notes:
        context["reviewer_notes"] = reviewer_notes
    return await wrapper.pipeline.run(context)
