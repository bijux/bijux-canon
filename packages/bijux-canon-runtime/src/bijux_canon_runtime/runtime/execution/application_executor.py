# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Execution service for persisted typed Runtime request plans."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import replace
from pathlib import Path
import threading

from bijux_canon_runtime.application.request_planner import RuntimeRequestPlanner
from bijux_canon_runtime.model.artifact import AddressedArtifact
from bijux_canon_runtime.model.execution.request_plan import (
    RuntimeOperationRequest,
    RuntimeRequestPlan,
)
from bijux_canon_runtime.model.execution.run_identity import (
    AttemptRelation,
    ExecutionAttemptIdentity,
    SemanticRunIdentity,
    SemanticRunInputs,
)
from bijux_canon_runtime.observability.storage.execution_store_lock import (
    acquire_execution_store_lock,
)
from bijux_canon_runtime.ontology.ids import RequestID, RunID
from bijux_canon_runtime.runtime.execution.dag_scheduler import (
    ArtifactTransitionJournal,
    DependencyAwareScheduler,
    SchedulerPolicy,
)
from bijux_canon_runtime.runtime.execution.operation_dispatcher import (
    OperationDispatcher,
)
from bijux_canon_runtime.runtime.execution.runtime_event_ledger import (
    RuntimeEventLedger,
)
from bijux_canon_runtime.runtime.inspection import RuntimeRunInspector
from bijux_canon_runtime.runtime.inspection.models import InspectedAttempt
from bijux_canon_runtime.runtime.persistence.payload_store import (
    DurableArtifactPayloadStore,
)

_PROCESS_RUN_LOCKS: dict[Path, threading.Lock] = {}
_PROCESS_RUN_LOCKS_GUARD = threading.Lock()


def _process_run_lock(path: Path) -> threading.Lock:
    with _PROCESS_RUN_LOCKS_GUARD:
        return _PROCESS_RUN_LOCKS.setdefault(path.resolve(), threading.Lock())


class RuntimeFirstExecutionError(RuntimeError):
    """A Runtime execution could not produce one complete persisted attempt."""


class RuntimeExecutionService:
    """Plan, schedule, persist, and inspect linked Runtime attempts."""

    def __init__(
        self,
        *,
        store: DurableArtifactPayloadStore,
        dispatcher: OperationDispatcher,
        process_id: str,
        configuration_identity_sha256: str,
        max_workers: int = 4,
    ) -> None:
        if not process_id.strip():
            raise ValueError("Runtime execution process identity is required")
        if max_workers < 1:
            raise ValueError("Runtime execution worker count must be positive")
        if len(configuration_identity_sha256) != 64 or any(
            character not in "0123456789abcdef"
            for character in configuration_identity_sha256
        ):
            raise ValueError("Runtime execution configuration identity is invalid")
        self._store = store
        self._dispatcher = dispatcher
        self._process_id = process_id
        self._configuration_identity_sha256 = configuration_identity_sha256
        self._max_workers = max_workers
        self._planner = RuntimeRequestPlanner()
        self._inspector = RuntimeRunInspector(store)

    def execute(
        self,
        request: RuntimeOperationRequest,
        is_cancelled: Callable[[], bool],
    ) -> Mapping[str, object]:
        """Execute one artifact-resolved request through its complete typed DAG."""
        request = replace(
            request,
            execution_configuration_sha256=self._configuration_identity_sha256,
        )
        source_selection: AddressedArtifact | None = None
        resolved_corpus_id = request.corpus_id
        if resolved_corpus_id is None and request.source_directory is not None:
            source_selection = AddressedArtifact.from_json(
                {
                    "root": str(Path(request.source_directory).resolve()),
                    "schema_version": "bijux.runtime.source-selection.v1",
                },
                schema_id="ingest.source-selection.v1",
                producer="bijux-canon-runtime:source-selection",
            )
            self._store.put(source_selection)
            resolved_corpus_id = source_selection.descriptor.artifact_id
        if resolved_corpus_id is None and request.index_id is None:
            raise RuntimeFirstExecutionError(
                "first execution requires a resolved corpus or index artifact"
            )
        if source_selection is not None:
            request = replace(
                request,
                source_selection_artifact_id=(source_selection.descriptor.artifact_id),
            )
        plan = self._planner.plan(request)
        run = SemanticRunIdentity.derive(
            SemanticRunInputs(
                operation=request.operation,
                scope=request.scope,
                query=request.query,
                corpus_artifact_id=resolved_corpus_id,
                index_artifact_id=request.index_id,
                filters=request.filters,
                top_k=request.top_k,
                output_policy=request.output_policy,
                execution_configuration_sha256=(request.execution_configuration_sha256),
            )
        )
        lock_path = self._store.root / "run-locks" / f"{run.run_id}.lock"
        with (
            _process_run_lock(lock_path),
            acquire_execution_store_lock(
                lock_path,
                timeout_seconds=request.budget.timeout_seconds,
            ),
        ):
            return self._execute_attempt(
                request=request,
                plan=plan,
                run=run,
                source_selection=source_selection,
                is_cancelled=is_cancelled,
            )

    def _execute_attempt(
        self,
        *,
        request: RuntimeOperationRequest,
        plan: RuntimeRequestPlan,
        run: SemanticRunIdentity,
        source_selection: AddressedArtifact | None,
        is_cancelled: Callable[[], bool],
    ) -> Mapping[str, object]:
        attempt = self._next_attempt(run, request.request_id)
        journal = ArtifactTransitionJournal(
            store=self._store,
            plan_sha256=plan.plan_sha256,
        )
        ledger = RuntimeEventLedger(
            store=self._store,
            plan=plan,
            attempt=attempt,
            execution_metadata={
                "execution_kind": attempt.relation.value,
                "parent_job_id": request.parent_job_id,
                "process_id": self._process_id,
            },
            manifest_dependencies=(
                ()
                if source_selection is None
                else (source_selection.descriptor.artifact_id,)
            ),
        )
        schedule = DependencyAwareScheduler(
            dispatcher=self._dispatcher,
            policy=SchedulerPolicy.for_plan(
                plan,
                max_workers=self._max_workers,
                max_resource_units=self._max_workers,
            ),
            journal=journal,
            events=ledger,
        ).run(plan, is_cancelled=is_cancelled)
        inspection = self._inspector.inspect(
            str(run.run_id),
            attempt_id=attempt.attempt_id,
        )
        if not schedule.succeeded:
            failures = "; ".join(
                f"{step_id}: {message}" for step_id, message in schedule.failures
            )
            raise RuntimeFirstExecutionError(
                f"Runtime run {run.run_id} did not complete: {failures}"
            )
        terminal_step_ids = set(plan.terminal_step_ids)
        terminal_artifact_ids = [
            str(artifact.artifact_id)
            for result in schedule.dispatch_results
            if result.step_id in terminal_step_ids
            for artifact in result.artifacts
        ]
        return {
            "attempt_id": attempt.attempt_id,
            "plan_sha256": plan.plan_sha256,
            "run_id": str(run.run_id),
            "schema_version": "bijux.runtime.execution-result.v2",
            "status": inspection.status.value,
            "terminal_artifact_ids": terminal_artifact_ids,
            "transition_artifact_ids": [
                str(item) for item in schedule.transition_artifact_ids
            ],
        }

    def _next_attempt(
        self,
        run: SemanticRunIdentity,
        request_id: RequestID,
    ) -> ExecutionAttemptIdentity:
        try:
            inspection = self._inspector.inspect(str(run.run_id))
        except KeyError:
            return ExecutionAttemptIdentity.initial(
                run=run,
                request_id=request_id,
                process_id=self._process_id,
            )
        latest = max(inspection.attempts, key=lambda item: item.attempt_number)
        return ExecutionAttemptIdentity.retry_persisted(
            request_id=request_id,
            source=_attempt_identity(latest, str(run.run_id)),
            process_id=self._process_id,
        )


def _attempt_identity(
    attempt: InspectedAttempt,
    run_id: str,
) -> ExecutionAttemptIdentity:
    return ExecutionAttemptIdentity(
        attempt_id=attempt.attempt_id,
        run_id=RunID(run_id),
        request_id=RequestID(attempt.request_id),
        attempt_number=attempt.attempt_number,
        relation=AttemptRelation(attempt.relation),
        source_attempt_id=attempt.source_attempt_id,
        supersedes_attempt_id=attempt.supersedes_attempt_id,
        retry_id=attempt.retry_id,
        replay_id=attempt.replay_id,
        process_id=attempt.process_id,
    )


RuntimeFirstExecutionService = RuntimeExecutionService


__all__ = [
    "RuntimeExecutionService",
    "RuntimeFirstExecutionError",
    "RuntimeFirstExecutionService",
]
