"""TaskHandlerAgent module for executing stages in a multi-agent system.

This module provides the TaskHandlerAgent class, which manages the execution
of a sequence of stages in a multi-agent system. It focuses on task execution
without orchestration, providing detailed logging and telemetry.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import time
from typing import Any, NotRequired, TypedDict, cast

from bijux_agent.agents.base import BaseAgent
from bijux_agent.utilities.logger_manager import LoggerManager, MetricType


class TaskHandlerAuditEntry(TypedDict, total=False):
    """TypedDict for audit trail entries."""

    stage_name: str
    timestamp: str
    duration_sec: float
    error: str
    stages_processed: list[str]


class TaskHandlerFinalStatus(TypedDict):
    """TypedDict for the final status block."""

    stages_processed: list[str]
    iterations: int


class TaskHandlerResult(TypedDict):
    """TypedDict describing the TaskHandlerAgent run output."""

    stages: dict[str, dict[str, Any]]
    final_status: TaskHandlerFinalStatus
    audit_trail: list[TaskHandlerAuditEntry]
    warnings: list[str]
    error: NotRequired[str]
    action_plan: NotRequired[list[str]]


class TaskHandlerAgent(BaseAgent):
    """Enhanced TaskHandlerAgent for executing a seq of stages in a multi-agent system.

    Manages stage execution with detailed logging and telemetry, focusing on
    task execution without orchestration.
    """

    def __init__(
        self,
        config: dict[str, Any],
        logger_manager: LoggerManager,
    ):
        """Initialize the TaskHandlerAgent with configuration and logger manager.

        Args:
            config: Configuration settings for the agent.
            logger_manager: The LoggerManager instance for logging and telemetry.
        """
        super().__init__(config, logger_manager)
        self._cache: dict[str, dict[str, Any]] | None = (
            {} if self.config.get("enable_cache", True) else None
        )
        self._stages: list[dict[str, Any]] = []  # Store stages to be executed

        self.logger.info(
            "TaskHandlerAgent initialized",
            extra={"context": {"config": {"enable_cache": bool(self._cache)}}},
        )

    def _initialize(self) -> None:
        """Initialize the agent by setting up any necessary resources.

        Currently, no additional initialization is required beyond what's done in
        __init__.
        """
        pass

    def _cleanup(self) -> None:
        """Clean up resources used by the agent.

        Currently, no additional cleanup is required.
        """
        pass

    def set_stages(self, stages: Sequence[Mapping[str, Any]]) -> None:
        """Set the list of stages to be executed by the TaskHandlerAgent.

        Args:
            stages: List of stage configurations to execute.
        """
        self._stages = [dict(stage) for stage in stages]
        self.logger.info(
            "Stages set for TaskHandlerAgent",
            extra={"context": {"stages": [stage["name"] for stage in self._stages]}},
        )

    @property
    def capabilities(self) -> list[str]:
        """List of capabilities this agent supports."""
        return ["task_handling"]

    async def _run_payload(self, context: dict[str, Any]) -> TaskHandlerResult:
        """Execute a sequence of stages with the provided context.

        Args:
            context: Input context containing initial data (e.g., file_path, task_goal).

        Returns:
            Dictionary containing stage results, final status, and audit trail.
        """
        if not self._stages:
            error_msg = "No stages set for TaskHandlerAgent to execute"
            self.logger.error(error_msg, extra={"context": {"stage": "init"}})
            self.logger_manager.log_metric(
                "stage_errors", 1, MetricType.COUNTER, tags={"stage": "init"}
            )
            return cast(
                TaskHandlerResult,
                await self.execution_kernel.error_result(error_msg, context, "init"),
            )

        context_id = context.get("context_id", "unknown")
        with self.logger.context(agent="TaskHandlerAgent", context_id=context_id):
            self.logger.info(
                "Starting stage execution",
                extra={
                    "context": {
                        "stage": "init",
                        "context_id": context_id,
                        "stages": [stage["name"] for stage in self._stages],
                    }
                },
            )

        # Initialize result structure
        start_time = time.perf_counter()
        result: TaskHandlerResult = {
            "stages": {},
            "final_status": {"stages_processed": [], "iterations": 0},
            "audit_trail": [],
            "warnings": [],
        }

        # Validate context
        if "file_path" not in context:
            error_msg = "Input context must provide 'file_path' for stage execution"
            self.logger.error(
                error_msg, extra={"context": {"stage": "input_validation"}}
            )
            self.logger_manager.log_metric(
                "input_validation_errors",
                1,
                MetricType.COUNTER,
                tags={"stage": "input_validation"},
            )
            return cast(
                TaskHandlerResult,
                await self.execution_kernel.error_result(
                    error_msg, context, "input_validation"
                ),
            )

        # Execute each stage in sequence
        current_context = context.copy()
        for stage in self._stages:
            stage_name = stage["name"]
            self.logger.debug(
                f"Executing stage: {stage_name}",
                extra={"context": {"stage": stage_name}},
            )

            # Check stage condition
            condition = stage.get("condition", lambda _: True)
            if not condition(current_context):
                warning_msg = f"Stage '{stage_name}' skipped due to unmet condition"
                self.logger.warning(
                    warning_msg, extra={"context": {"stage": stage_name}}
                )
                result["warnings"].append(warning_msg)
                continue

            # Prepare inputs for the stage
            inputs = {}
            for dependency in stage.get("dependencies", []):
                if dependency in result["stages"]:
                    inputs.update(result["stages"][dependency])
            inputs.update(current_context)

            # Execute the stage
            try:
                stage_start_time = time.perf_counter()
                stage_output = await self._execute_stage(stage, inputs)
                stage_duration = time.perf_counter() - stage_start_time

                # Update result with stage output
                result["stages"][stage_name] = stage_output
                result["final_status"]["stages_processed"].append(stage_name)
                result["audit_trail"].append(
                    {
                        "stage_name": stage_name,
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "duration_sec": round(stage_duration, 2),
                    }
                )
                self.logger_manager.log_metric(
                    "stage_duration",
                    stage_duration,
                    MetricType.HISTOGRAM,
                    tags={"stage": stage_name},
                )

                # Check for errors in stage output
                if "error" in stage_output:
                    error_msg = f"Stage '{stage_name}' failed: {stage_output['error']}"
                    self.logger.error(
                        error_msg, extra={"context": {"stage": stage_name}}
                    )
                    self.logger_manager.log_metric(
                        "stage_errors",
                        1,
                        MetricType.COUNTER,
                        tags={"stage": stage_name},
                    )
                    result["warnings"].append(error_msg)
                    continue

                # Update context with stage output
                output_key = stage.get("output_key", stage_name)
                current_context[output_key] = stage_output

            except Exception as e:
                error_msg = f"Stage '{stage_name}' execution failed: {e!s}"
                self.logger.error(
                    error_msg, extra={"context": {"stage": stage_name, "error": str(e)}}
                )
                self.logger_manager.log_metric(
                    "stage_errors", 1, MetricType.COUNTER, tags={"stage": stage_name}
                )
                result["warnings"].append(error_msg)
                continue

        # Finalize result
        duration = time.perf_counter() - start_time
        result["audit_trail"].append(
            {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "duration_sec": round(duration, 2),
                "stages_processed": result["final_status"]["stages_processed"],
            }
        )

        self.logger.info(
            "Stage execution completed successfully",
            extra={
                "context": {
                    "stage": "completion",
                    "duration_sec": duration,
                    "stages_processed": result["final_status"]["stages_processed"],
                }
            },
        )
        self.logger_manager.log_metric(
            "task_duration",
            duration,
            MetricType.HISTOGRAM,
            tags={"stage": "completion"},
        )

        return result

    async def _execute_stage(
        self, stage: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute a single stage with the given context.

        Args:
            stage: Stage configuration containing agent(s) and settings.
            context: Input context for the stage.

        Returns:
            Stage output dictionary.
        """
        stage_name = stage["name"]
        self.logger.debug(
            f"Executing stage {stage_name} with context: {context}",
            extra={"context": {"stage": stage_name}},
        )

        if "agents" in stage:
            # Ensemble mode: multiple agents with weights
            results = []
            weights = []
            for agent_entry in stage["agents"]:
                agent = agent_entry["agent"]
                weight = agent_entry["weight"]
                try:
                    agent_result = await agent.run(context)
                    results.append(agent_result)
                    weights.append(weight)
                except Exception as e:
                    self.logger.error(
                        f"Agent in stage '{stage_name}' failed: {e!s}",
                        extra={"context": {"stage": stage_name}},
                    )
                    return {"error": str(e)}
            # Simple weighted merge (example implementation)
            if results:
                # Simplified; could implement actual weighted merging
                merged_result = results[0]
                return merged_result
            return {"error": "No successful agent results"}
        else:
            # Single agent execution
            agent = stage["agent"]
            try:
                return await agent.run(context)
            except Exception as e:
                self.logger.error(
                    f"Agent in stage '{stage_name}' failed: {e!s}",
                    extra={"context": {"stage": stage_name}},
                )
                return {"error": str(e)}

    def error_payload(
        self,
        msg: str,
        context: dict[str, Any],
        stage: str,
        extra: dict[str, Any] | None = None,
    ) -> TaskHandlerResult:
        """Return a standardized error result with async logging."""
        _ = extra
        self.logger_manager.log_metric(
            "task_errors", 1, MetricType.COUNTER, tags={"stage": stage}
        )
        return {
            "stages": {},
            "final_status": {"stages_processed": [], "iterations": 0},
            "audit_trail": [
                {
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "duration_sec": 0.0,
                    "error": msg,
                }
            ],
            "warnings": [msg],
            "error": msg,
            "action_plan": [f"Resolve error: {msg}"],
        }

    @classmethod
    def self_report_schema(cls) -> dict[str, Any]:
        """Return the output schema for documentation and validation."""
        return {
            "stages": "dict",
            "final_status": {"stages_processed": "list[str]", "iterations": "int"},
            "audit_trail": "list[dict]",
            "warnings": "list[str]",
            "error": "str (if error occurred)",
            "action_plan": "list[str]",
        }

    @classmethod
    def coverage_report(cls, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Describe the parts of the context this agent consumes or modifies."""
        return {
            "consumes": ["file_path", "task_goal"],
            "modifies": [],
            "produces": ["stages", "final_status", "audit_trail"],
        }

    def flush_logs(self) -> None:
        """Flush all log handlers."""
        try:
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

    async def get_telemetry(self) -> dict[str, dict[str, Any]]:
        """Retrieve telemetry metrics.

        Returns:
            Dictionary of telemetry metrics.
        """
        try:
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

    def reset_telemetry(self) -> None:
        """Reset telemetry metrics."""
        try:
            self.logger_manager.reset_metrics()
            self.logger.debug(
                "Telemetry metrics reset",
                extra={"context": {"stage": "reset_telemetry"}},
            )
            self.logger_manager.log_metric(
                "metrics_reset",
                1,
                MetricType.COUNTER,
                tags={"stage": "reset_telemetry"},
            )
        except Exception as e:
            self.logger.error(
                f"Failed to reset telemetry: {e!s}",
                extra={"context": {"stage": "reset_telemetry", "error": str(e)}},
            )

    async def shutdown(self) -> None:
        """Shutdown the agent and flush logs."""
        self.logger.info(
            "Shutting down TaskHandlerAgent", extra={"context": {"stage": "shutdown"}}
        )
        self.flush_logs()
        self.logger.info(
            "TaskHandlerAgent shutdown complete",
            extra={"context": {"stage": "shutdown"}},
        )
        await super().shutdown()
