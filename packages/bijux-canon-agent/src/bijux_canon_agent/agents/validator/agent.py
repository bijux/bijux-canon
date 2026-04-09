"""ValidatorAgent module for Bijux Agent.

This module provides the ValidatorAgent class, which performs deep,
schema-aware validation of nested data structures, such as LLM outputs.
It supports type coercion, conditional rules, regex patterns, range
checks, and custom plugins, providing detailed status, errors, warnings,
audit trails, and telemetry.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import time
from typing import Any, cast

from bijux_canon_agent.agents.base import BaseAgent
from bijux_canon_agent.observability.logging import LoggerManager, MetricType

from .rules import (
    reporting,
    rule_execution,
)
from .rules import (
    schema as schema_walker,
)
from .run_context import (
    apply_pre_hook,
    build_validation_run_context,
    cache_schema,
)
from .validation_issues import (
    collect_extra_key_warning,
    run_custom_validation_issues,
)


class ValidationError(Exception):
    """Exception for validation failures, used for strict mode."""


class ValidatorAgent(BaseAgent):
    """Enhanced ValidatorAgent for a multi-agent system.

    Performs deep, schema-aware validation of nested data structures
    (e.g., LLM outputs). Supports type coercion, conditional rules,
    regex patterns, range checks, and custom plugins. Provides detailed
    status, errors, warnings, audit trails, and telemetry.
    """

    def __init__(
        self,
        config: dict[str, Any],
        logger_manager: LoggerManager,
        schema: dict[str, Any] | None = None,
        custom_validator: Callable[
            [dict[str, Any], dict[str, Any]], dict[str, Any] | Awaitable[dict[str, Any]]
        ]
        | None = None,
        pre_hook: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        post_hook: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]
        | None = None,
    ):
        """Initialize the ValidatorAgent with configuration and logger manager.

        Args:
            config:
                Configuration settings (strictness, error policy, type_cast, etc.).
            logger_manager:
                The LoggerManager instance for logging.
            schema:
                Validation schema (supports nested structures, types, allowed values,
                etc.).
            custom_validator:
                Optional function (data, config) -> dict for additional checks.
            pre_hook:
                Optional function called before validation (e.g., transform data).
            post_hook:
                Optional function called after validation (e.g., add audit info).
        """
        super().__init__(config, logger_manager)
        self.schema = schema or self.config.get("schema", {})
        self.custom_validator = custom_validator or self.config.get("custom_validator")
        self.pre_hook = pre_hook
        self.post_hook = post_hook
        self.type_cast = bool(self.config.get("type_cast", True))
        self.strict = bool(self.config.get("strict", False))
        self.allow_extra = bool(self.config.get("allow_extra", not self.strict))
        self.soft_failure = bool(self.config.get("soft_failure", False))
        self._schema_cache: dict[str, dict[str, Any]] = {}
        self._validation_plugins: list[
            Callable[[Any, dict[str, Any], str], tuple[list[str], dict[str, Any]]]
        ] = []

        self.logger.info(
            "ValidatorAgent initialized",
            extra={
                "context": {
                    "config": {
                        "type_cast": self.type_cast,
                        "strict": self.strict,
                        "allow_extra": self.allow_extra,
                        "soft_failure": self.soft_failure,
                        "schema_keys": list(self.schema.keys()),
                    }
                }
            },
        )

    def _initialize(self) -> None:
        """Initialize the agent by setting up any necessary resources.

        Currently, no additional initialization is required beyond what's done in
        __init__.
        """

    @property
    def capabilities(self) -> list[str]:
        """List of capabilities this agent supports."""
        return ["validation"]

    async def _run_payload(self, context: dict[str, Any]) -> dict[str, Any]:
        """Entry point for validation (async).

        Validates data against the schema, applies custom validators and plugins,
        and returns detailed status, errors, warnings, audit info, and schema snapshot.

        Args:
            context: Input context containing the data to validate under 'data'.

        Returns:
            Dictionary containing validation results.
        """
        run_context = build_validation_run_context(context, self.schema)
        with self.logger.context(
            agent="ValidatorAgent",
            context_id=run_context.context_id,
        ):
            self.logger.info(
                "Starting validation operation",
                extra={
                    "context": {"stage": "init", "context_id": run_context.context_id}
                },
            )

        data = run_context.data

        start_time = time.perf_counter()
        errors: list[str] = []
        warnings: list[str] = []
        audit: dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        }

        # Pre-hook
        data, pre_hook_error = apply_pre_hook(
            data,
            pre_hook=self.pre_hook,
            logger=self.logger,
            logger_manager=self.logger_manager,
        )
        if pre_hook_error is not None:
            return await reporting.error_result(
                self,
                pre_hook_error,
                context,
                "pre_hook",
            )

        # Cache schema hash for optimization
        cache_schema(
            schema_hash=run_context.schema_hash,
            schema=self.schema,
            schema_cache=self._schema_cache,
            logger=self.logger,
            logger_manager=self.logger_manager,
        )

        # Core validation
        validation_errors, validation_audit = schema_walker.validate_recursive(
            self, data, self.schema, path=""
        )
        errors.extend(validation_errors)
        audit.update(validation_audit)

        # Custom validator
        custom_errors, custom_warnings = await run_custom_validation_issues(
            self,
            data=data,
            audit=audit,
            run_custom_validator=rule_execution.run_custom_validator,
        )
        errors.extend(custom_errors)
        warnings.extend(custom_warnings)

        # Extra keys check
        warning_msg = collect_extra_key_warning(
            data=data,
            schema_keys=set(schema_walker.get_all_schema_keys(self.schema)),
            data_keys=set(schema_walker.get_all_data_keys(data))
            if isinstance(data, dict)
            else set(),
            strict=self.strict,
            allow_extra=self.allow_extra,
        )
        if warning_msg is not None:
            warnings.append(warning_msg)
            self.logger.warning(
                warning_msg, extra={"context": {"stage": "extra_keys_check"}}
            )

        plugin_errors = rule_execution.run_validation_plugins(self, data, audit)
        errors.extend(plugin_errors)

        duration = time.perf_counter() - start_time
        result, status = reporting.build_validation_result(
            self, data, errors, warnings, audit, duration
        )

        if self.post_hook:
            try:
                result = self.post_hook(cast(dict[str, Any], data), result)
                self.logger.debug(
                    "Post-hook applied successfully",
                    extra={"context": {"stage": "post_hook"}},
                )
                self.logger_manager.log_metric(
                    "post_hook_success",
                    1,
                    MetricType.COUNTER,
                    tags={"stage": "post_hook"},
                )
            except Exception as e:
                error_msg = f"Post-hook failed: {e!s}"
                self.logger.warning(
                    error_msg,
                    extra={"context": {"stage": "post_hook", "error": str(e)}},
                )
                self.logger_manager.log_metric(
                    "post_hook_errors",
                    1,
                    MetricType.COUNTER,
                    tags={"stage": "post_hook"},
                )
                warnings.append(error_msg)

        reporting.log_validation_completion(self, result, status, duration)

        await self.logger.async_log(
            "INFO",
            "Validation operation completed",
            {
                "status": status,
                "duration_sec": result["duration_sec"],
                "context_id": run_context.context_id,
            },
        )

        if self.strict and not result["valid"] and not self.soft_failure:
            raise ValidationError(f"Validation failed: {errors}")

        return result

    async def get_telemetry(self) -> dict[str, dict[str, Any]]:
        """Retrieve telemetry metrics.

        Returns:
            Dictionary of telemetry metrics.
        """
        try:
            # LoggerManager.get_metrics() is synchronous and returns a dict
            metrics = self.logger_manager.get_metrics()
            self.logger.debug(
                "Telemetry retrieved",
                extra={
                    "context": {
                        "stage": "telemetry",
                        "metric_names": list(metrics.keys()),
                    }
                },
            )
            self.logger_manager.log_metric(
                "telemetry_retrieved",
                1,
                MetricType.COUNTER,
                tags={"stage": "telemetry"},
            )
            return metrics
        except Exception as e:
            self.logger.error(
                f"Failed to retrieve telemetry: {e!s}",
                extra={"context": {"stage": "telemetry", "error": str(e)}},
            )
            return {}

    def flush_logs(self) -> None:
        """Flush all log handlers."""
        try:
            # LoggerManager.flush() is synchronous and returns None
            self.logger_manager.flush()
            self.logger.debug("Logs flushed", extra={"context": {"stage": "log_flush"}})
            self.logger_manager.log_metric(
                "log_flush", 1, MetricType.COUNTER, tags={"stage": "log_flush"}
            )
        except Exception as e:
            self.logger.error(
                f"Failed to flush logs: {e!s}",
                extra={"context": {"stage": "log_flush", "error": str(e)}},
            )

    async def shutdown(self) -> None:
        """Shutdown the agent and flush logs."""
        self.logger.info(
            "Shutting down ValidatorAgent", extra={"context": {"stage": "shutdown"}}
        )
        self.flush_logs()
        self.logger.info(
            "ValidatorAgent shutdown complete", extra={"context": {"stage": "shutdown"}}
        )
        await super().shutdown()
