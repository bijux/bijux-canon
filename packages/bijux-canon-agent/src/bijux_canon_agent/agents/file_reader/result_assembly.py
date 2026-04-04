"""Helpers for assembling file-reader results."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from bijux_canon_agent.observability.logging import (
    CustomLogger,
    LoggerManager,
    MetricType,
)

from .reporting import build_file_agent_audit
from .telemetry_support import build_auto_enrichments


def apply_extra_analyzers(
    read_result: dict[str, Any],
    analyzers: list[Callable[[dict[str, Any]], dict[str, Any]]],
    *,
    logger: CustomLogger,
    logger_manager: LoggerManager,
) -> None:
    """Apply analyzer enrichments to the read result in place."""
    enrichments: dict[str, Any] = {}
    for analyzer in analyzers:
        try:
            analyzer_result = analyzer(read_result)
            enrichments.update(analyzer_result)
            logger.debug(
                f"Applied analyzer: {analyzer.__name__}",
                extra={
                    "context": {
                        "stage": "analyzer",
                        "analyzer_keys": list(analyzer_result.keys()),
                    }
                },
            )
            logger_manager.log_metric(
                "analyzer_success",
                1,
                MetricType.COUNTER,
                tags={"stage": "analyzer", "analyzer": analyzer.__name__},
            )
        except Exception as exc:
            logger.warning(
                f"Analyzer {analyzer.__name__} failed: {exc!s}",
                extra={"context": {"stage": "analyzer", "error": str(exc)}},
            )
            logger_manager.log_metric(
                "analyzer_errors",
                1,
                MetricType.COUNTER,
                tags={"stage": "analyzer", "analyzer": analyzer.__name__},
            )
    if enrichments:
        read_result["enrichments"] = enrichments
        logger.debug(
            "Enrichments applied",
            extra={
                "context": {
                    "stage": "enrichments",
                    "enrichment_keys": list(enrichments.keys()),
                }
            },
        )


def apply_post_hook(
    context: dict[str, Any],
    read_result: dict[str, Any],
    *,
    post_hook: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]] | None,
    logger: CustomLogger,
    logger_manager: LoggerManager,
) -> dict[str, Any]:
    """Apply the optional post-hook to the read result."""
    if post_hook is None:
        return read_result
    try:
        updated_result = post_hook(context, read_result)
        logger.debug(
            "Post-hook applied successfully",
            extra={"context": {"stage": "post_hook"}},
        )
        logger_manager.log_metric(
            "post_hook_success",
            1,
            MetricType.COUNTER,
            tags={"stage": "post_hook"},
        )
        return updated_result
    except Exception as exc:
        logger.warning(
            f"Post-hook failed: {exc!s}",
            extra={"context": {"stage": "post_hook", "error": str(exc)}},
        )
        logger_manager.log_metric(
            "post_hook_errors",
            1,
            MetricType.COUNTER,
            tags={"stage": "post_hook"},
        )
        return read_result


def finalize_read_result(
    read_result: dict[str, Any],
    *,
    context: dict[str, Any],
    post_hook: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]] | None,
    file_path: str,
    context_id: str,
    file_suffix: str,
    agent_version: str,
    agent_id: str,
    cache_enabled: bool,
    async_io: bool,
    logger: CustomLogger,
    logger_manager: LoggerManager,
) -> dict[str, Any]:
    """Attach enrichments, post-processing, and audit data to a read result."""
    read_result.update(
        build_auto_enrichments(
            read_result,
            logger=logger,
            logger_manager=logger_manager,
            agent_name="FileReaderAgent",
        )
    )
    finalized_result = apply_post_hook(
        context,
        read_result,
        post_hook=post_hook,
        logger=logger,
        logger_manager=logger_manager,
    )
    finalized_result["file_agent_audit"] = build_file_agent_audit(
        file_path,
        agent_version=agent_version,
        agent_id=agent_id,
        cache_enabled=cache_enabled,
        async_io=async_io,
        context_id=context_id,
        file_type=file_suffix,
    )
    return finalized_result
