"""Telemetry helpers for pipeline execution contexts."""

from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Any, TypedDict


class PipelineTelemetry(TypedDict, total=False):
    """Structured telemetry emitted by every pipeline execution."""

    iterations: int
    stages_executed: int
    total_duration: float
    shards_processed: int


@dataclass
class PipelineExecutionContext:
    """Encapsulates the mutable telemetry state for a single pipeline run."""

    audit_trail: list[dict[str, Any]]
    revision_history: list[dict[str, Any]]
    start_time: float = field(default_factory=time.time)

    def baseline(self) -> PipelineTelemetry:
        """Return a zeroed telemetry snapshot before execution finishes."""

        return {"iterations": 0, "stages_executed": 0}

    def finalize(self, shards_processed: int) -> PipelineTelemetry:
        """Produce the definitive telemetry snapshot when the run completes."""

        return {
            "iterations": len(self.revision_history),
            "stages_executed": len(self.audit_trail),
            "total_duration": time.time() - self.start_time,
            "shards_processed": shards_processed,
        }
