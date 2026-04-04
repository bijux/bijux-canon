"""Issue aggregation helpers for validator execution."""

from __future__ import annotations

from typing import Any, cast

from bijux_canon_agent.observability.logging import MetricType


async def run_custom_validation_issues(
    agent: Any,
    *,
    data: Any,
    audit: dict[str, Any],
    run_custom_validator: Any,
) -> tuple[list[str], list[str]]:
    """Run the optional custom validator and return collected issues."""
    if agent.custom_validator is None:
        return [], []
    try:
        user_result = await run_custom_validator(
            agent,
            cast(dict[str, Any], data),
            agent.config,
        )
        audit["custom_validator"] = user_result.get("details", {})
        agent.logger.debug(
            "Custom validator applied",
            extra={"context": {"stage": "custom_validator"}},
        )
        agent.logger_manager.log_metric(
            "custom_validator_success",
            1,
            MetricType.COUNTER,
            tags={"stage": "custom_validator"},
        )
        return user_result.get("errors", []), user_result.get("warnings", [])
    except Exception as exc:
        error_msg = f"Custom validator failed: {exc!s}"
        agent.logger.error(
            error_msg,
            extra={"context": {"stage": "custom_validator", "error": str(exc)}},
        )
        agent.logger_manager.log_metric(
            "custom_validator_errors",
            1,
            MetricType.COUNTER,
            tags={"stage": "custom_validator"},
        )
        return [error_msg], []


def collect_extra_key_warning(
    *,
    data: Any,
    schema_keys: set[str],
    data_keys: set[str],
    strict: bool,
    allow_extra: bool,
) -> str | None:
    """Return the extra-key warning for strict schema validation when needed."""
    if not strict or not isinstance(data, dict) or allow_extra:
        return None
    extra_keys = data_keys - schema_keys
    if not extra_keys:
        return None
    return f"Unexpected extra keys: {sorted(extra_keys)}"


__all__ = ["collect_extra_key_warning", "run_custom_validation_issues"]
