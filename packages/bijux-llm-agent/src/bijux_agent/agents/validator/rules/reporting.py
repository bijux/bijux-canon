"""Reporting helpers for ValidatorAgent."""

from __future__ import annotations

import time
from typing import Any

from bijux_agent.utilities.logger_manager import MetricType


def build_validation_result(
    agent: Any,
    data: Any,
    errors: list[str],
    warnings: list[str],
    audit: dict[str, Any],
    duration: float,
) -> tuple[dict[str, Any], str]:
    """Construct the structured validation result."""
    status = "valid" if not errors else "invalid"
    valid = not errors
    result = {
        "validation_status": status,
        "valid": valid,
        "errors": errors,
        "warnings": warnings,
        "audit": audit,
        "schema": agent.schema,
        "duration_sec": round(duration, 4),
        "action_plan": (
            [f"Fix validation error: {error}" for error in errors] if errors else []
        ),
    }
    return result, status


def log_validation_completion(
    agent: Any,
    result: dict[str, Any],
    status: str,
    duration: float,
) -> None:
    """Log completion metrics and async info."""
    errors = result["errors"]
    warnings = result["warnings"]
    agent.logger.info(
        "Validation completed",
        extra={
            "context": {
                "stage": "completion",
                "status": status,
                "duration_sec": result["duration_sec"],
                "error_count": len(errors),
                "warning_count": len(warnings),
            }
        },
    )
    agent.logger_manager.log_metric(
        "validation_duration",
        duration,
        MetricType.HISTOGRAM,
        tags={"stage": "completion", "status": status},
    )
    agent.logger_manager.log_metric(
        "validation_errors",
        len(errors),
        MetricType.COUNTER,
        tags={"stage": "completion"},
    )
    agent.logger_manager.log_metric(
        "validation_warnings",
        len(warnings),
        MetricType.COUNTER,
        tags={"stage": "completion"},
    )


def persistence_error(
    agent: Any, msg: str, context: dict[str, Any] | None, stage: str
) -> dict[str, Any]:
    """Build an error result dictionary for failures in the run loop."""
    result = {
        "validation_status": "invalid",
        "valid": False,
        "errors": [msg],
        "warnings": [],
        "audit": {
            "stage": stage,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        },
        "schema": agent.schema,
        "duration_sec": 0.0,
        "action_plan": [f"Fix error: {msg}"],
    }
    return result


async def error_result(
    agent: Any, msg: str, context: dict[str, Any], stage: str
) -> dict[str, Any]:
    """Log an error and return the associated validation payload."""
    result = persistence_error(agent, msg, context, stage)
    await agent.logger.async_log(
        "ERROR",
        msg,
        {"stage": stage, "context_id": context.get("context_id", "unknown")},
    )
    return result
