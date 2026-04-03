"""Typed dictionaries shared between pipeline execution modules."""

from __future__ import annotations

from typing import Any, NotRequired, Required, TypedDict

from bijux_agent.pipeline.termination import ExecutionTerminationReason


class PipelineTelemetry(TypedDict, total=False):
    """Structured telemetry emitted by every pipeline execution."""

    iterations: int
    stages_executed: int
    total_duration: float
    shards_processed: int


class FinalStatus(TypedDict):
    """Final status returned for each stage or shard."""

    stages_processed: Required[list[str]]
    iterations: Required[int]
    success: Required[bool]
    termination_reason: ExecutionTerminationReason
    error: NotRequired[str]
    score: NotRequired[float]
    critique_status: NotRequired[str]
    converged: NotRequired[bool]
    convergence_reason: NotRequired[str | None]
    convergence_iterations: NotRequired[int]


class ShardResult(TypedDict):
    """Result of a single shard run."""

    stages: dict[str, Any]
    audit_trail: list[dict[str, Any]]
    revision_history: list[dict[str, Any]]
    execution_path: list[dict[str, Any]]
    warnings: list[str]
    final_status: FinalStatus
    error: NotRequired[str]
    action_plan: NotRequired[list[str]]


class IterationResult(TypedDict):
    """Trace of a single iteration inside a shard."""

    iteration: int
    stages: dict[str, Any]


class PipelineExecutionResult(TypedDict):
    """Canonical response emitted by `Pipeline.run()`."""

    result: dict[str, Any] | None
    stages: dict[str, Any]
    audit_trail: list[dict[str, Any]]
    final_status: FinalStatus
    cache_hit: bool
    revision_history: list[dict[str, Any]]
    telemetry: PipelineTelemetry
    execution_path: list[dict[str, Any]]
    warnings: list[str]
    error: NotRequired[str]
    action_plan: NotRequired[list[str]]


class MergedShardResult(TypedDict):
    """Merged outcome of multiple shards."""

    stages: dict[str, Any]
    final_status: FinalStatus
