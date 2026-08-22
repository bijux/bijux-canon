# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Supersede interrupted attempts without repeating admitted effects."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from bijux_canon_runtime.model.execution.request_plan import (
    ConcreteDagStep,
    DagOperation,
)
from bijux_canon_runtime.model.execution.run_identity import (
    AttemptRelation,
    ExecutionAttemptIdentity,
)
from bijux_canon_runtime.ontology.ids import RequestID, RunID
from bijux_canon_runtime.ontology.public import ReplayMode
from bijux_canon_runtime.runtime.execution.dag_scheduler import (
    ArtifactTransitionJournal,
    DependencyAwareScheduler,
    SchedulerPolicy,
)
from bijux_canon_runtime.runtime.execution.operation_dispatcher import (
    OperationAdapter,
    OperationDispatcher,
    StepDispatchContext,
    StepOutputArtifact,
)
from bijux_canon_runtime.runtime.execution.runtime_event_ledger import (
    RuntimeEventLedger,
)
from bijux_canon_runtime.runtime.inspection import (
    InspectedAttempt,
    InspectedDagStep,
    InspectedRunStatus,
    InspectedStepStatus,
    RuntimeRunInspection,
    RuntimeRunInspector,
)
from bijux_canon_runtime.runtime.persistence.filesystem_payload_store import (
    AtomicFilesystemArtifactPayloadStore,
)
from bijux_canon_runtime.runtime.recovery.models import (
    RecoveredStep,
    RecoveryStepDisposition,
    RuntimeRecoveryError,
    RuntimeRecoveryOutcome,
)
from bijux_canon_runtime.runtime.replay.plan_reconstruction import (
    reconstruct_linked_plan,
)
from bijux_canon_runtime.runtime.replay.recorded_adapter import (
    RecordedReplayAdapter,
)


@dataclass(frozen=True, slots=True)
class _RecoveryAdapter:
    operation: DagOperation
    source_steps: dict[str, InspectedDagStep]
    store: AtomicFilesystemArtifactPayloadStore
    live_adapter: OperationAdapter | None
    reconciliation_adapter: OperationAdapter | None
    adapter_id: str = "bijux-canon-runtime:interruption-recovery:v1"
    adapter_version: str = "1.0"

    def execute(
        self,
        step: ConcreteDagStep,
        upstream: tuple[StepOutputArtifact, ...],
        context: StepDispatchContext,
    ) -> tuple[StepOutputArtifact, ...]:
        """Reuse completed outputs and explicitly resolve ambiguous starts."""
        source = self.source_steps[step.step_id]
        if source.status is InspectedStepStatus.COMPLETED:
            return RecordedReplayAdapter(
                self.operation,
                self.source_steps,
                self.store,
            ).execute(step, upstream, context)
        if source.status in {
            InspectedStepStatus.RUNNING,
            InspectedStepStatus.FAILED,
        }:
            if self.reconciliation_adapter is None:
                raise RuntimeRecoveryError(
                    f"started step requires an idempotent reconciler: {step.step_id}"
                )
            return self.reconciliation_adapter.execute(step, upstream, context)
        if source.status not in {
            InspectedStepStatus.PLANNED,
            InspectedStepStatus.SKIPPED,
        }:
            raise RuntimeRecoveryError(
                f"source step cannot be recovered from {source.status.value}"
            )
        if self.live_adapter is None:
            raise RuntimeRecoveryError(
                f"planned step has no execution adapter: {step.step_id}"
            )
        return self.live_adapter.execute(step, upstream, context)


class RuntimeRecoveryService:
    """Create a linked retry from the latest incomplete persisted attempt."""

    def __init__(self, store: AtomicFilesystemArtifactPayloadStore) -> None:
        self._store = store
        self._inspector = RuntimeRunInspector(store)

    def recover(
        self,
        *,
        run_id: str,
        source_attempt_id: str,
        request_id: RequestID,
        process_id: str,
        live_adapters: Mapping[DagOperation, OperationAdapter],
        reconciliation_adapters: Mapping[DagOperation, OperationAdapter] | None = None,
        scheduler_policy: SchedulerPolicy | None = None,
        is_cancelled: Callable[[], bool] | None = None,
    ) -> RuntimeRecoveryOutcome:
        """Supersede an interruption while preserving every admitted output."""
        current = self._inspector.inspect(run_id)
        source = self._inspector.inspect(run_id, attempt_id=source_attempt_id)
        existing = next(
            (item for item in current.attempts if item.request_id == str(request_id)),
            None,
        )
        if existing is not None:
            return self._reuse_existing(source, existing)
        if current.selected_attempt_id != source_attempt_id:
            raise RuntimeRecoveryError("recovery must supersede the latest attempt")
        if source.status not in {
            InspectedRunStatus.RUNNING,
            InspectedRunStatus.FAILED,
        }:
            raise RuntimeRecoveryError(
                "recovery requires an interrupted or failed attempt"
            )
        reconciliation = dict(reconciliation_adapters or {})
        ambiguous_statuses = {
            InspectedStepStatus.RUNNING,
            InspectedStepStatus.FAILED,
        }
        ambiguous = {
            step.operation
            for step in source.steps
            if step.status in ambiguous_statuses
        }
        missing = ambiguous.difference(item.value for item in reconciliation)
        if missing:
            raise RuntimeRecoveryError(
                "started operations require reconcilers: " + ", ".join(sorted(missing))
            )
        source_identity = _attempt_identity(
            next(item for item in source.attempts if item.attempt_id == source_attempt_id),
            run_id,
        )
        retry = ExecutionAttemptIdentity.retry_persisted(
            request_id=request_id,
            source=source_identity,
            process_id=process_id,
        )
        replay_mode = ReplayMode(source.events[0].policy["replay_mode"])
        reconstruction = reconstruct_linked_plan(
            source,
            request_id=request_id,
            replay_mode=replay_mode,
            linkage_kind="recovery",
            execution_policy={
                "ambiguous_step_ids": [
                    step.step_id
                    for step in source.steps
                    if step.status in ambiguous_statuses
                ]
            },
        )
        plan = reconstruction.plan
        source_steps = {step.step_id: step for step in source.steps}
        adapters = tuple(
            _RecoveryAdapter(
                operation,
                source_steps,
                self._store,
                live_adapters.get(operation),
                reconciliation.get(operation),
            )
            for operation in dict.fromkeys(step.operation for step in plan.steps)
        )
        policy = scheduler_policy or SchedulerPolicy.for_plan(
            plan,
            max_workers=4,
            max_resource_units=4,
        )
        journal = ArtifactTransitionJournal(
            store=self._store,
            plan_sha256=plan.plan_sha256,
        )
        ledger = RuntimeEventLedger(
            store=self._store,
            plan=plan,
            attempt=retry,
            execution_metadata={
                "recovery": {
                    "source_attempt_id": source_attempt_id,
                    "source_event_head_artifact_id": str(
                        source.events[-1].artifact_id
                    ),
                    "source_output_artifact_ids": [
                        str(artifact_id)
                        for step in source.steps
                        for artifact_id in step.output_artifact_ids
                    ],
                    "source_failure_event_artifact_ids": [
                        str(failure.event_artifact_id)
                        for failure in source.failures
                    ],
                    "ambiguous_step_ids": [
                        step.step_id
                        for step in source.steps
                        if step.status in ambiguous_statuses
                    ],
                }
            },
            manifest_dependencies=(source.events[-1].artifact_id,),
        )
        schedule = DependencyAwareScheduler(
            dispatcher=OperationDispatcher(adapters),
            policy=policy,
            journal=journal,
            events=ledger,
        ).run(plan, is_cancelled=is_cancelled)
        recovered = self._inspector.inspect(run_id, attempt_id=retry.attempt_id)
        return RuntimeRecoveryOutcome(
            source=source,
            recovery=recovered,
            steps=_recovered_steps(source, recovered),
            retained_source_artifact_ids=tuple(
                item.artifact_id for item in source.artifacts
            ),
            transition_artifact_ids=schedule.transition_artifact_ids,
            reused=False,
        )

    def _reuse_existing(
        self,
        source: RuntimeRunInspection,
        existing: InspectedAttempt,
    ) -> RuntimeRecoveryOutcome:
        if (
            existing.relation != AttemptRelation.RETRY.value
            or existing.source_attempt_id != source.selected_attempt_id
        ):
            raise RuntimeRecoveryError(
                "recovery request identity is bound to another attempt"
            )
        recovered = self._inspector.inspect(
            source.run_id,
            attempt_id=existing.attempt_id,
        )
        return RuntimeRecoveryOutcome(
            source,
            recovered,
            _recovered_steps(source, recovered),
            tuple(item.artifact_id for item in source.artifacts),
            (),
            True,
        )


def _attempt_identity(attempt: InspectedAttempt, run_id: str) -> ExecutionAttemptIdentity:
    return ExecutionAttemptIdentity(
        attempt.attempt_id,
        RunID(run_id),
        RequestID(attempt.request_id),
        attempt.attempt_number,
        AttemptRelation(attempt.relation),
        attempt.source_attempt_id,
        attempt.supersedes_attempt_id,
        attempt.retry_id,
        attempt.replay_id,
        attempt.process_id,
    )


def _recovered_steps(
    source: RuntimeRunInspection,
    recovered: RuntimeRunInspection,
) -> tuple[RecoveredStep, ...]:
    recovered_by_id = {step.step_id: step for step in recovered.steps}
    dispositions = {
        InspectedStepStatus.COMPLETED: RecoveryStepDisposition.REUSED,
        InspectedStepStatus.RUNNING: RecoveryStepDisposition.RECONCILED,
        InspectedStepStatus.FAILED: RecoveryStepDisposition.RECONCILED,
        InspectedStepStatus.PLANNED: RecoveryStepDisposition.EXECUTED,
        InspectedStepStatus.SKIPPED: RecoveryStepDisposition.EXECUTED,
    }
    return tuple(
        RecoveredStep(
            step.step_id,
            step.operation,
            dispositions[step.status],
            step.output_artifact_ids,
            recovered_by_id[step.step_id].output_artifact_ids,
        )
        for step in source.steps
    )


__all__ = ["RuntimeRecoveryService"]
