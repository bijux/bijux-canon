# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""First-execution service for persisted typed Runtime request plans."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path

from bijux_canon_runtime.application.request_planner import RuntimeRequestPlanner
from bijux_canon_runtime.model.artifact import AddressedArtifact
from bijux_canon_runtime.model.execution.request_plan import RuntimeOperationRequest
from bijux_canon_runtime.model.execution.run_identity import (
    ExecutionAttemptIdentity,
    SemanticRunIdentity,
    SemanticRunInputs,
)
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
from bijux_canon_runtime.runtime.persistence.filesystem_payload_store import (
    AtomicFilesystemArtifactPayloadStore,
)


class RuntimeFirstExecutionError(RuntimeError):
    """A first execution could not produce one complete persisted attempt."""


class RuntimeFirstExecutionService:
    """Plan, schedule, persist, and inspect one initial Runtime attempt."""

    def __init__(
        self,
        *,
        store: AtomicFilesystemArtifactPayloadStore,
        dispatcher: OperationDispatcher,
        process_id: str,
        max_workers: int = 4,
    ) -> None:
        if not process_id.strip():
            raise ValueError("Runtime execution process identity is required")
        if max_workers < 1:
            raise ValueError("Runtime execution worker count must be positive")
        self._store = store
        self._dispatcher = dispatcher
        self._process_id = process_id
        self._max_workers = max_workers
        self._planner = RuntimeRequestPlanner()
        self._inspector = RuntimeRunInspector(store)

    def execute(
        self,
        request: RuntimeOperationRequest,
        is_cancelled: Callable[[], bool],
    ) -> Mapping[str, object]:
        """Execute one artifact-resolved request through its complete typed DAG."""

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
            )
        )
        attempt = ExecutionAttemptIdentity.initial(
            run=run,
            request_id=request.request_id,
            process_id=self._process_id,
        )
        journal = ArtifactTransitionJournal(
            store=self._store,
            plan_sha256=plan.plan_sha256,
        )
        ledger = RuntimeEventLedger(
            store=self._store,
            plan=plan,
            attempt=attempt,
            execution_metadata={
                "execution_kind": "initial",
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


__all__ = ["RuntimeFirstExecutionError", "RuntimeFirstExecutionService"]
