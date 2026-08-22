# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Dependency-aware scheduling for typed Runtime request plans."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import StrEnum
import threading

from bijux_canon_runtime.model.artifact import AddressedArtifact
from bijux_canon_runtime.model.execution.request_plan import (
    ConcreteDagStep,
    RuntimeRequestPlan,
)
from bijux_canon_runtime.ontology.ids import ArtifactID
from bijux_canon_runtime.runtime.execution.operation_dispatcher import (
    OperationDispatcher,
    StepDispatchCancelled,
    StepDispatchContext,
    StepDispatchResult,
    StepOutputArtifact,
)
from bijux_canon_runtime.runtime.persistence.payload_store import ArtifactPayloadStore


class SchedulerError(RuntimeError):
    """A DAG cannot be scheduled within its declared constraints."""


class StepNodeStatus(StrEnum):
    """Durable scheduler states for one typed DAG node."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class StepSchedulingConstraint:
    """Resource demand and exclusive write ownership for one node."""

    step_id: str
    resource_units: int
    write_keys: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.step_id.strip() or self.resource_units < 1:
            raise ValueError("scheduler constraints require a step and resources")
        if any(not item.strip() for item in self.write_keys):
            raise ValueError("scheduler write keys must not be empty")
        if len(set(self.write_keys)) != len(self.write_keys):
            raise ValueError("scheduler write keys must be unique")


@dataclass(frozen=True, slots=True)
class SchedulerPolicy:
    """Complete concurrency policy for one immutable plan."""

    max_workers: int
    max_resource_units: int
    constraints: tuple[StepSchedulingConstraint, ...]

    def __post_init__(self) -> None:
        if self.max_workers < 1 or self.max_resource_units < 1:
            raise ValueError("scheduler concurrency limits must be positive")
        step_ids = tuple(item.step_id for item in self.constraints)
        if len(step_ids) != len(set(step_ids)):
            raise ValueError("scheduler constraints must have unique step identities")
        if any(
            item.resource_units > self.max_resource_units
            for item in self.constraints
        ):
            raise ValueError("step resource demand exceeds scheduler capacity")

    @classmethod
    def for_plan(
        cls,
        plan: RuntimeRequestPlan,
        *,
        max_workers: int,
        max_resource_units: int,
        resource_units: int = 1,
    ) -> SchedulerPolicy:
        """Declare a bounded default policy with explicit durable write keys."""
        return cls(
            max_workers=max_workers,
            max_resource_units=max_resource_units,
            constraints=tuple(
                StepSchedulingConstraint(
                    step_id=step.step_id,
                    resource_units=resource_units,
                    write_keys=_default_write_keys(step),
                )
                for step in plan.steps
            ),
        )


def _default_write_keys(step: ConcreteDagStep) -> tuple[str, ...]:
    if step.operation.value == "persist":
        return (f"run:{step.inputs.request_id}",)
    if step.operation.value == "publish":
        return (f"publication:{step.inputs.request_id}",)
    return ()


@dataclass(frozen=True, slots=True)
class SchedulerTransition:
    """One hash-chained scheduler state transition."""

    sequence: int
    plan_sha256: str
    step_id: str
    from_status: StepNodeStatus | None
    to_status: StepNodeStatus
    occurred_at: str
    failure_type: str | None = None
    failure_message: str | None = None


class ArtifactTransitionJournal:
    """Persist scheduler transitions as immutable dependency-linked artifacts."""

    def __init__(
        self,
        *,
        store: ArtifactPayloadStore,
        plan_sha256: str,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._store = store
        self._plan_sha256 = plan_sha256
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._records: list[SchedulerTransition] = []
        self._artifact_ids: list[ArtifactID] = []
        self._lock = threading.Lock()

    def append(
        self,
        *,
        step_id: str,
        from_status: StepNodeStatus | None,
        to_status: StepNodeStatus,
        failure: Exception | None = None,
    ) -> SchedulerTransition:
        """Validate, persist, and retain one transition before continuing."""
        with self._lock:
            self._validate_transition(step_id, from_status, to_status)
            record = SchedulerTransition(
                sequence=len(self._records),
                plan_sha256=self._plan_sha256,
                step_id=step_id,
                from_status=from_status,
                to_status=to_status,
                occurred_at=self._clock().isoformat(),
                failure_type=None if failure is None else type(failure).__name__,
                failure_message=None if failure is None else str(failure),
            )
            artifact = AddressedArtifact.from_json(
                asdict(record),
                schema_id="bijux.runtime.scheduler-transition.v1",
                producer="bijux-canon-runtime:scheduler",
                dependencies=(self._artifact_ids[-1],) if self._artifact_ids else (),
            )
            self._store.put(artifact)
            self._records.append(record)
            self._artifact_ids.append(artifact.descriptor.artifact_id)
            return record

    @property
    def records(self) -> tuple[SchedulerTransition, ...]:
        """Return transitions in their persisted deterministic order."""
        return tuple(self._records)

    @property
    def plan_sha256(self) -> str:
        """Return the immutable plan identity owned by this journal."""
        return self._plan_sha256

    @property
    def artifact_ids(self) -> tuple[ArtifactID, ...]:
        """Return the immutable transition artifact chain."""
        return tuple(self._artifact_ids)

    def _validate_transition(
        self,
        step_id: str,
        from_status: StepNodeStatus | None,
        to_status: StepNodeStatus,
    ) -> None:
        current = next(
            (
                record.to_status
                for record in reversed(self._records)
                if record.step_id == step_id
            ),
            None,
        )
        if current is not from_status:
            raise SchedulerError("scheduler transition does not match persisted state")
        allowed = {
            None: {StepNodeStatus.QUEUED},
            StepNodeStatus.QUEUED: {
                StepNodeStatus.RUNNING,
                StepNodeStatus.BLOCKED,
                StepNodeStatus.CANCELLED,
            },
            StepNodeStatus.RUNNING: {
                StepNodeStatus.SUCCEEDED,
                StepNodeStatus.FAILED,
                StepNodeStatus.CANCELLED,
            },
        }
        if to_status not in allowed.get(from_status, set()):
            raise SchedulerError("scheduler state transition is not permitted")


@dataclass(frozen=True, slots=True)
class DagScheduleResult:
    """Complete scheduler outcome with branch-local failures."""

    plan_sha256: str
    statuses: tuple[tuple[str, StepNodeStatus], ...]
    dispatch_results: tuple[StepDispatchResult, ...]
    failures: tuple[tuple[str, str], ...]
    transition_artifact_ids: tuple[ArtifactID, ...]

    @property
    def succeeded(self) -> bool:
        """Return whether every node completed successfully."""
        return all(status is StepNodeStatus.SUCCEEDED for _, status in self.statuses)


class DependencyAwareScheduler:
    """Execute safe ready sets and isolate failures to their descendants."""

    def __init__(
        self,
        *,
        dispatcher: OperationDispatcher,
        policy: SchedulerPolicy,
        journal: ArtifactTransitionJournal,
    ) -> None:
        self._dispatcher = dispatcher
        self._policy = policy
        self._journal = journal

    def run(
        self,
        plan: RuntimeRequestPlan,
        *,
        is_cancelled: Callable[[], bool] | None = None,
    ) -> DagScheduleResult:
        """Run the plan until every node is terminal or cancellation wins."""
        if plan.plan_sha256 != self._journal.plan_sha256:
            raise SchedulerError("scheduler journal belongs to another plan")
        constraints = {item.step_id: item for item in self._policy.constraints}
        step_ids = {step.step_id for step in plan.steps}
        if set(constraints) != step_ids:
            raise SchedulerError("scheduler policy must cover every plan step exactly")
        cancelled = is_cancelled or (lambda: False)
        statuses = dict.fromkeys(step_ids, StepNodeStatus.QUEUED)
        outputs: dict[str, tuple[StepOutputArtifact, ...]] = {}
        results: dict[str, StepDispatchResult] = {}
        failures: dict[str, str] = {}
        for step in plan.steps:
            self._journal.append(
                step_id=step.step_id,
                from_status=None,
                to_status=StepNodeStatus.QUEUED,
            )

        with ThreadPoolExecutor(max_workers=self._policy.max_workers) as executor:
            while any(status is StepNodeStatus.QUEUED for status in statuses.values()):
                self._block_failed_descendants(plan, statuses)
                queued = [
                    step
                    for step in plan.steps
                    if statuses[step.step_id] is StepNodeStatus.QUEUED
                ]
                if not queued:
                    break
                if cancelled():
                    for step in queued:
                        statuses[step.step_id] = StepNodeStatus.CANCELLED
                        self._journal.append(
                            step_id=step.step_id,
                            from_status=StepNodeStatus.QUEUED,
                            to_status=StepNodeStatus.CANCELLED,
                        )
                    break
                ready = [
                    step
                    for step in queued
                    if all(
                        statuses[dependency] is StepNodeStatus.SUCCEEDED
                        for dependency in step.depends_on
                    )
                ]
                if not ready:
                    raise SchedulerError("queued nodes have no satisfiable dependencies")
                wave = self._select_wave(ready, constraints)
                futures = {}
                for step in wave:
                    statuses[step.step_id] = StepNodeStatus.RUNNING
                    self._journal.append(
                        step_id=step.step_id,
                        from_status=StepNodeStatus.QUEUED,
                        to_status=StepNodeStatus.RUNNING,
                    )
                    upstream = tuple(
                        artifact
                        for dependency in step.depends_on
                        for artifact in outputs[dependency]
                    )
                    futures[step.step_id] = executor.submit(
                        self._dispatcher.dispatch,
                        step,
                        upstream,
                        context=StepDispatchContext(cancelled),
                    )
                for step in wave:
                    future = futures[step.step_id]
                    try:
                        result = future.result()
                    except StepDispatchCancelled as exc:
                        statuses[step.step_id] = StepNodeStatus.CANCELLED
                        failures[step.step_id] = str(exc)
                        self._journal.append(
                            step_id=step.step_id,
                            from_status=StepNodeStatus.RUNNING,
                            to_status=StepNodeStatus.CANCELLED,
                            failure=exc,
                        )
                    except Exception as exc:
                        statuses[step.step_id] = StepNodeStatus.FAILED
                        failures[step.step_id] = str(exc)
                        self._journal.append(
                            step_id=step.step_id,
                            from_status=StepNodeStatus.RUNNING,
                            to_status=StepNodeStatus.FAILED,
                            failure=exc,
                        )
                    else:
                        statuses[step.step_id] = StepNodeStatus.SUCCEEDED
                        outputs[step.step_id] = result.artifacts
                        results[step.step_id] = result
                        self._journal.append(
                            step_id=step.step_id,
                            from_status=StepNodeStatus.RUNNING,
                            to_status=StepNodeStatus.SUCCEEDED,
                        )

        return DagScheduleResult(
            plan_sha256=plan.plan_sha256,
            statuses=tuple((step.step_id, statuses[step.step_id]) for step in plan.steps),
            dispatch_results=tuple(
                results[step.step_id]
                for step in plan.steps
                if step.step_id in results
            ),
            failures=tuple(
                (step.step_id, failures[step.step_id])
                for step in plan.steps
                if step.step_id in failures
            ),
            transition_artifact_ids=self._journal.artifact_ids,
        )

    def _block_failed_descendants(
        self,
        plan: RuntimeRequestPlan,
        statuses: dict[str, StepNodeStatus],
    ) -> None:
        changed = True
        while changed:
            changed = False
            for step in plan.steps:
                if statuses[step.step_id] is not StepNodeStatus.QUEUED:
                    continue
                blocking_dependencies = tuple(
                    dependency
                    for dependency in step.depends_on
                    if statuses[dependency]
                    in {
                        StepNodeStatus.FAILED,
                        StepNodeStatus.BLOCKED,
                        StepNodeStatus.CANCELLED,
                    }
                )
                if blocking_dependencies:
                    statuses[step.step_id] = StepNodeStatus.BLOCKED
                    failure = SchedulerError(
                        "dependency did not succeed: "
                        + ", ".join(sorted(blocking_dependencies))
                    )
                    self._journal.append(
                        step_id=step.step_id,
                        from_status=StepNodeStatus.QUEUED,
                        to_status=StepNodeStatus.BLOCKED,
                        failure=failure,
                    )
                    changed = True

    def _select_wave(
        self,
        ready: list[ConcreteDagStep],
        constraints: dict[str, StepSchedulingConstraint],
    ) -> tuple[ConcreteDagStep, ...]:
        selected: list[ConcreteDagStep] = []
        resource_units = 0
        write_keys: set[str] = set()
        for step in ready:
            constraint = constraints[step.step_id]
            if len(selected) == self._policy.max_workers:
                break
            if resource_units + constraint.resource_units > (
                self._policy.max_resource_units
            ):
                continue
            if write_keys.intersection(constraint.write_keys):
                continue
            selected.append(step)
            resource_units += constraint.resource_units
            write_keys.update(constraint.write_keys)
        if not selected:
            raise SchedulerError("ready nodes cannot satisfy scheduler constraints")
        return tuple(selected)


__all__ = [
    "ArtifactTransitionJournal",
    "DagScheduleResult",
    "DependencyAwareScheduler",
    "SchedulerError",
    "SchedulerPolicy",
    "SchedulerTransition",
    "StepNodeStatus",
    "StepSchedulingConstraint",
]
