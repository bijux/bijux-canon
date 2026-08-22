# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Tests for dependency-aware scheduling and its persisted event boundary."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
import json
from pathlib import Path
import threading
from time import monotonic, sleep

from bijux_canon_runtime.application.request_planner import RuntimeRequestPlanner
from bijux_canon_runtime.model.execution.request_plan import (
    ConcreteDagStep,
    DagOperation,
    ExecutionProfile,
    RetrievalFilters,
    RuntimeOperationRequest,
    RuntimeRequestBudget,
    RuntimeRequestOperation,
    RuntimeRequestPlan,
)
from bijux_canon_runtime.model.execution.run_identity import (
    ExecutionAttemptIdentity,
    SemanticRunIdentity,
    SemanticRunInputs,
)
from bijux_canon_runtime.ontology.ids import ArtifactID, RequestID
from bijux_canon_runtime.ontology.public import ReplayMode
from bijux_canon_runtime.runtime.execution.dag_scheduler import (
    ArtifactTransitionJournal,
    DagScheduleResult,
    DependencyAwareScheduler,
    SchedulerPolicy,
    StepNodeStatus,
    StepSchedulingConstraint,
)
from bijux_canon_runtime.runtime.execution.operation_dispatcher import (
    OperationDispatcher,
    StepDispatchContext,
    StepOutputArtifact,
    resolved_input_artifact_ids,
)
from bijux_canon_runtime.runtime.execution.runtime_event_ledger import (
    RuntimeEventKind,
    RuntimeEventLedger,
)
from bijux_canon_runtime.runtime.persistence import (
    AtomicFilesystemArtifactPayloadStore,
)


@dataclass(slots=True)
class _ConcurrencyProbe:
    active: int = 0
    maximum_active: int = 0
    calls: int = 0
    lock: threading.Lock = field(default_factory=threading.Lock)

    def enter(self) -> None:
        with self.lock:
            self.active += 1
            self.maximum_active = max(self.maximum_active, self.active)
            self.calls += 1

    def leave(self) -> None:
        with self.lock:
            self.active -= 1


@dataclass(frozen=True, slots=True)
class _OperationAdapter:
    operation: DagOperation
    probe: _ConcurrencyProbe
    barrier: threading.Barrier | None = None
    fail: bool = False

    @property
    def adapter_id(self) -> str:
        return f"test:{self.operation.value}"

    @property
    def adapter_version(self) -> str:
        return "1"

    def execute(
        self,
        step: ConcreteDagStep,
        upstream: tuple[StepOutputArtifact, ...],
        context: StepDispatchContext,
    ) -> tuple[StepOutputArtifact, ...]:
        context.raise_if_stopped()
        self.probe.enter()
        try:
            if self.barrier is not None:
                self.barrier.wait(timeout=5)
            else:
                sleep(0.01)
            if self.fail:
                raise RuntimeError("deliberate branch-local failure")
            dependencies = resolved_input_artifact_ids(step, upstream)
            return tuple(
                StepOutputArtifact.from_payload(
                    step=step,
                    contract_id=contract_id,
                    media_type="application/json",
                    payload=json.dumps(
                        {
                            "operation": step.operation.value,
                            "step_id": step.step_id,
                        },
                        sort_keys=True,
                    ).encode(),
                    dependency_artifact_ids=dependencies,
                )
                for contract_id in step.output_artifact_contract_ids
            )
        finally:
            self.probe.leave()


def _index_plan() -> RuntimeRequestPlan:
    return RuntimeRequestPlanner().plan(
        RuntimeOperationRequest(
            request_id=RequestID("request-scheduler-test"),
            operation=RuntimeRequestOperation.INDEX_BUILD,
            execution_profile=ExecutionProfile.LOCAL_HYBRID_EXACT,
            budget=RuntimeRequestBudget(
                timeout_seconds=30.0,
                max_artifact_bytes=10_000_000,
            ),
            replay_mode=ReplayMode.STRICT,
            scope="scheduler-test",
            corpus_id=ArtifactID("sha256:" + "a" * 64),
        )
    )


def _attempt(plan: RuntimeRequestPlan, process_id: str) -> ExecutionAttemptIdentity:
    run = SemanticRunIdentity.derive(
        SemanticRunInputs(
            operation=RuntimeRequestOperation.INDEX_BUILD,
            scope="scheduler-test",
            query=None,
            corpus_artifact_id=plan.steps[0].inputs.corpus_id,
            index_artifact_id=None,
            filters=RetrievalFilters(),
            top_k=None,
            output_policy=None,
        )
    )
    return ExecutionAttemptIdentity.initial(
        run=run,
        request_id=plan.request_id,
        process_id=process_id,
    )


def _run(
    tmp_path: Path,
    *,
    parallel_barrier: bool = False,
    fail_embed: bool = False,
    shared_write_key: bool = False,
    record_events: bool = False,
    is_cancelled: Callable[[], bool] | None = None,
    deadline_monotonic: float | None = None,
    monotonic_clock: Callable[[], float] = monotonic,
) -> tuple[
    DagScheduleResult,
    _ConcurrencyProbe,
    RuntimeEventLedger | None,
    AtomicFilesystemArtifactPayloadStore,
]:
    plan = _index_plan()
    store = AtomicFilesystemArtifactPayloadStore(tmp_path / "artifacts")
    journal = ArtifactTransitionJournal(
        store=store,
        plan_sha256=plan.plan_sha256,
    )
    events = (
        RuntimeEventLedger(
            store=store,
            plan=plan,
            attempt=_attempt(plan, f"process-{tmp_path.name}"),
            execution_metadata={"profile": "focused-test"},
        )
        if record_events
        else None
    )
    probe = _ConcurrencyProbe()
    barrier = threading.Barrier(2) if parallel_barrier else None
    adapters = tuple(
        _OperationAdapter(
            operation=step.operation,
            probe=probe,
            barrier=(
                barrier
                if step.operation in {DagOperation.EMBED, DagOperation.LEXICAL_INDEX}
                else None
            ),
            fail=fail_embed and step.operation is DagOperation.EMBED,
        )
        for step in plan.steps
    )
    constraints = tuple(
        StepSchedulingConstraint(
            step_id=step.step_id,
            resource_units=1,
            write_keys=(("index-writer",) if shared_write_key else ()),
        )
        for step in plan.steps
    )
    result = DependencyAwareScheduler(
        dispatcher=OperationDispatcher(adapters),
        policy=SchedulerPolicy(
            max_workers=2,
            max_resource_units=2,
            constraints=constraints,
        ),
        journal=journal,
        events=events,
    ).run(
        plan,
        is_cancelled=is_cancelled,
        deadline_monotonic=deadline_monotonic,
        monotonic_clock=monotonic_clock,
    )
    reopened = AtomicFilesystemArtifactPayloadStore(tmp_path / "artifacts")
    for artifact_id in result.transition_artifact_ids:
        reopened.load(artifact_id)
    return result, probe, events, reopened


def test_scheduler_runs_independent_nodes_concurrently_and_persists_transitions(
    tmp_path: Path,
) -> None:
    result, probe, _, _ = _run(tmp_path, parallel_barrier=True)

    assert result.succeeded
    assert probe.maximum_active == 2
    assert dict(result.statuses) == {
        "embed": StepNodeStatus.SUCCEEDED,
        "lexical_index": StepNodeStatus.SUCCEEDED,
        "dense_index": StepNodeStatus.SUCCEEDED,
    }
    assert len(result.transition_artifact_ids) == 9


def test_scheduler_failure_blocks_only_descendants(tmp_path: Path) -> None:
    result, probe, _, _ = _run(tmp_path, fail_embed=True)

    assert dict(result.statuses) == {
        "embed": StepNodeStatus.FAILED,
        "lexical_index": StepNodeStatus.SUCCEEDED,
        "dense_index": StepNodeStatus.BLOCKED,
    }
    assert probe.calls == 2
    assert result.failures == (
        (
            "embed",
            "adapter test:embed failed operation embed",
        ),
    )


def test_scheduler_serializes_conflicting_write_owners(tmp_path: Path) -> None:
    result, probe, _, _ = _run(tmp_path, shared_write_key=True)

    assert result.succeeded
    assert probe.maximum_active == 1


def test_scheduler_persists_complete_success_and_failure_events(
    tmp_path: Path,
) -> None:
    success, _, success_events, success_store = _run(
        tmp_path / "success",
        parallel_barrier=True,
        record_events=True,
    )
    failure, _, failure_events, failure_store = _run(
        tmp_path / "failure",
        fail_embed=True,
        record_events=True,
    )
    assert success_events is not None
    assert failure_events is not None

    success_kinds = tuple(record.event_kind for record in success_events.records)
    failure_kinds = tuple(record.event_kind for record in failure_events.records)
    assert success.succeeded
    assert success_kinds.count(RuntimeEventKind.PLANNED) == 3
    assert success_kinds.count(RuntimeEventKind.STARTED) == 3
    assert success_kinds.count(RuntimeEventKind.COMPLETED) == 3
    assert RuntimeEventKind.FAILED in failure_kinds
    assert RuntimeEventKind.SKIPPED in failure_kinds
    assert dict(failure.statuses)["lexical_index"] is StepNodeStatus.SUCCEEDED

    completed = tuple(
        record
        for record in success_events.records
        if record.event_kind is RuntimeEventKind.COMPLETED
    )
    assert all(record.output_artifact_ids for record in completed)
    assert all(record.policy["execution_metadata"] for record in completed)
    failed = next(
        record
        for record in failure_events.records
        if record.event_kind is RuntimeEventKind.FAILED
    )
    assert failed.error is not None
    assert failed.error.error_type == "StepDispatchError"
    assert failed.error.causes == (("RuntimeError", "deliberate branch-local failure"),)

    success_store.load(success_events.manifest_artifact_id)
    failure_store.load(failure_events.manifest_artifact_id)
    for artifact_id in success_events.artifact_ids:
        success_store.load(artifact_id)
    for artifact_id in failure_events.artifact_ids:
        failure_store.load(artifact_id)


def test_scheduler_cancels_queued_nodes_without_dispatching(
    tmp_path: Path,
) -> None:
    result, probe, events, _ = _run(
        tmp_path,
        record_events=True,
        is_cancelled=lambda: True,
    )
    assert events is not None

    assert set(dict(result.statuses).values()) == {StepNodeStatus.CANCELLED}
    assert probe.calls == 0
    assert (
        tuple(record.event_kind for record in events.records).count(
            RuntimeEventKind.CANCELLED
        )
        == 3
    )


def test_scheduler_classifies_expired_deadline_separately_from_cancellation(
    tmp_path: Path,
) -> None:
    result, probe, events, _ = _run(
        tmp_path,
        record_events=True,
        deadline_monotonic=9.0,
        monotonic_clock=lambda: 10.0,
    )
    assert events is not None

    assert set(dict(result.statuses).values()) == {StepNodeStatus.TIMED_OUT}
    assert probe.calls == 0
    assert (
        tuple(record.event_kind for record in events.records).count(
            RuntimeEventKind.TIMED_OUT
        )
        == 3
    )
