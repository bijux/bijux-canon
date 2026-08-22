# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Module definitions for runtime/execution/__init__.py."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bijux_canon_runtime.runtime.execution.application_executor import (
    RuntimeExecutionService,
    RuntimeFirstExecutionError,
    RuntimeFirstExecutionService,
)
from bijux_canon_runtime.runtime.execution.dag_scheduler import (
    ArtifactTransitionJournal,
    DagScheduleResult,
    DependencyAwareScheduler,
    SchedulerError,
    SchedulerPolicy,
    SchedulerTransition,
    StepNodeStatus,
    StepSchedulingConstraint,
)
from bijux_canon_runtime.runtime.execution.durable_jobs import (
    DurableJobCancelled,
    DurableJobError,
    DurableJobHandler,
    DurableJobManager,
    DurableJobRequest,
    DurableJobSnapshot,
    DurableJobTimedOut,
    JobKind,
    JobStatus,
)
from bijux_canon_runtime.runtime.execution.operation_dispatcher import (
    OperationAdapter,
    OperationDispatcher,
    StepDispatchCancelled,
    StepDispatchContext,
    StepDispatchError,
    StepDispatchResult,
    StepDispatchTimedOut,
    StepOutputArtifact,
)
from bijux_canon_runtime.runtime.execution.runtime_event_ledger import (
    RuntimeErrorRecord,
    RuntimeEventKind,
    RuntimeEventLedger,
    RuntimeEventRecord,
)
from bijux_canon_runtime.runtime.execution.service_composition import (
    CanonicalServiceComposition,
    InstalledServiceCapability,
    compose_canonical_services,
)
from bijux_canon_runtime.runtime.execution.step_executor import ExecutionOutcome
from bijux_canon_runtime.runtime.inspection import (
    InspectedArtifact,
    InspectedAttempt,
    InspectedDagStep,
    InspectedErrorRecord,
    InspectedEvent,
    InspectedEventKind,
    InspectedFailure,
    InspectedRunStatus,
    InspectedStepStatus,
    PersistedInspectionValue,
    RuntimeInspectionError,
    RuntimeRunInspection,
    RuntimeRunInspector,
)

if TYPE_CHECKING:
    from bijux_canon_runtime.runtime.execution.application_composition import (
        compose_runtime_application_services,
    )

__all__ = [
    "ArtifactTransitionJournal",
    "DagScheduleResult",
    "DependencyAwareScheduler",
    "DurableJobCancelled",
    "DurableJobError",
    "DurableJobHandler",
    "DurableJobManager",
    "DurableJobRequest",
    "DurableJobSnapshot",
    "DurableJobTimedOut",
    "ExecutionOutcome",
    "CanonicalServiceComposition",
    "InstalledServiceCapability",
    "InspectedArtifact",
    "InspectedAttempt",
    "InspectedDagStep",
    "InspectedErrorRecord",
    "InspectedEvent",
    "InspectedEventKind",
    "InspectedFailure",
    "InspectedRunStatus",
    "InspectedStepStatus",
    "JobKind",
    "JobStatus",
    "OperationAdapter",
    "OperationDispatcher",
    "PersistedInspectionValue",
    "RuntimeInspectionError",
    "RuntimeExecutionService",
    "RuntimeFirstExecutionError",
    "RuntimeFirstExecutionService",
    "RuntimeErrorRecord",
    "RuntimeEventKind",
    "RuntimeEventLedger",
    "RuntimeEventRecord",
    "RuntimeRunInspection",
    "RuntimeRunInspector",
    "SchedulerError",
    "SchedulerPolicy",
    "SchedulerTransition",
    "StepDispatchCancelled",
    "StepDispatchContext",
    "StepDispatchError",
    "StepDispatchResult",
    "StepDispatchTimedOut",
    "StepOutputArtifact",
    "StepNodeStatus",
    "StepSchedulingConstraint",
    "compose_canonical_services",
    "compose_runtime_application_services",
]


def __getattr__(name: str) -> Any:
    """Load the application composition root only when explicitly requested."""

    if name == "compose_runtime_application_services":
        from bijux_canon_runtime.runtime.execution.application_composition import (
            compose_runtime_application_services,
        )

        globals()[name] = compose_runtime_application_services
        return compose_runtime_application_services
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """Include the lazy composition root in interactive discovery."""

    return sorted(set(globals()) | set(__all__))
