"""Run-context helpers for validator execution."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import hashlib
from typing import Any

from bijux_canon_agent.observability.logging import (
    CustomLogger,
    LoggerManager,
    MetricType,
)


@dataclass(frozen=True)
class ValidationRunContext:
    """Normalized validator run inputs and cache identity."""

    context_id: str
    data: Any
    schema_hash: str


def build_validation_run_context(
    context: dict[str, Any],
    schema: dict[str, Any],
) -> ValidationRunContext:
    """Normalize validator input data and derive its runtime identifiers."""
    context_id = context.get(
        "context_id", str(hashlib.sha256(str(context).encode()).hexdigest())
    )
    data: Any = context.get("data") if "data" in context else context
    schema_hash = hashlib.sha256(str(schema).encode()).hexdigest()
    return ValidationRunContext(
        context_id=context_id,
        data=data,
        schema_hash=schema_hash,
    )


def apply_pre_hook(
    data: Any,
    *,
    pre_hook: Callable[[dict[str, Any]], dict[str, Any]] | None,
    logger: CustomLogger,
    logger_manager: LoggerManager,
) -> tuple[Any, str | None]:
    """Apply the optional validator pre-hook."""
    if pre_hook is None:
        return data, None
    try:
        updated_data = pre_hook(data)
        logger.debug(
            "Pre-hook applied successfully",
            extra={"context": {"stage": "pre_hook"}},
        )
        logger_manager.log_metric(
            "pre_hook_success",
            1,
            MetricType.COUNTER,
            tags={"stage": "pre_hook"},
        )
        return updated_data, None
    except Exception as exc:
        error_msg = f"Pre-hook failed: {exc!s}"
        logger.error(
            error_msg,
            extra={"context": {"stage": "pre_hook", "error": str(exc)}},
        )
        logger_manager.log_metric(
            "pre_hook_errors",
            1,
            MetricType.COUNTER,
            tags={"stage": "pre_hook"},
        )
        return data, error_msg


def cache_schema(
    *,
    schema_hash: str,
    schema: dict[str, Any],
    schema_cache: dict[str, dict[str, Any]],
    logger: CustomLogger,
    logger_manager: LoggerManager,
) -> None:
    """Ensure the current schema snapshot is present in the cache."""
    if schema_hash not in schema_cache:
        schema_cache[schema_hash] = schema
        logger.debug(
            "Schema cached",
            extra={"context": {"stage": "schema_cache", "schema_hash": schema_hash}},
        )
        logger_manager.log_metric(
            "schema_cache_miss",
            1,
            MetricType.COUNTER,
            tags={"stage": "schema_cache"},
        )
        return
    logger.debug(
        "Schema cache hit",
        extra={"context": {"stage": "schema_cache", "schema_hash": schema_hash}},
    )
    logger_manager.log_metric(
        "schema_cache_hit",
        1,
        MetricType.COUNTER,
        tags={"stage": "schema_cache"},
    )
