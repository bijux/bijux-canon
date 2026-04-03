"""Rule execution helpers for ValidatorAgent."""

from __future__ import annotations

import asyncio
from typing import Any

from bijux_agent.utilities.logger_manager import MetricType


def run_validation_plugins(
    agent: Any, data: dict[str, Any], audit: dict[str, Any]
) -> list[str]:
    """Run registered validation plugins and update audit."""
    errors: list[str] = []
    for plugin in agent._validation_plugins:
        try:
            plugin_errors, plugin_audit = plugin(data, agent.schema, "plugin")
            errors.extend(plugin_errors)
            audit[f"plugin_{plugin.__name__}"] = plugin_audit
            agent.logger.debug(
                f"Validation plugin {plugin.__name__} applied",
                extra={"context": {"stage": "validation_plugin"}},
            )
            agent.logger_manager.log_metric(
                "validation_plugin_runs",
                1,
                MetricType.COUNTER,
                tags={"stage": "validation_plugin", "plugin": plugin.__name__},
            )
        except Exception as e:
            error_msg = f"Validation plugin {plugin.__name__} failed: {e!s}"
            errors.append(error_msg)
            agent.logger.error(
                error_msg,
                extra={"context": {"stage": "validation_plugin", "error": str(e)}},
            )
            agent.logger_manager.log_metric(
                "validation_plugin_errors",
                1,
                MetricType.COUNTER,
                tags={"stage": "validation_plugin", "plugin": plugin.__name__},
            )
    return errors


async def run_custom_validator(
    agent: Any, data: dict[str, Any], config: dict[str, Any]
) -> dict[str, Any]:
    """Invoke the custom validator, supporting both sync and async variants."""
    if asyncio.iscoroutinefunction(agent.custom_validator):
        result = await agent.custom_validator(data, config)
        return result  # type: ignore[return-value]
    result = await asyncio.to_thread(agent.custom_validator, data, config)
    return result  # type: ignore[return-value]
