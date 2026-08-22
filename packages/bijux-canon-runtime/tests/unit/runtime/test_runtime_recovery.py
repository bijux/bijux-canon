# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Tests for recovery from persisted interrupted Runtime attempts."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

import pytest

from bijux_canon_runtime.application.request_planner import RuntimeRequestPlanner
from bijux_canon_runtime.model.artifact import AddressedArtifact
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
from bijux_canon_runtime.runtime.execution.dag_scheduler import SchedulerError
from bijux_canon_runtime.runtime.execution.operation_dispatcher import (
    StepDispatchContext,
    StepOutputArtifact,
    resolved_input_artifact_ids,
)
from bijux_canon_runtime.runtime.execution.runtime_event_ledger import (
    RuntimeEventKind,
    RuntimeEventLedger,
)
from bijux_canon_runtime.runtime.inspection import (
    InspectedRunStatus,
    RuntimeRunInspector,
)
from bijux_canon_runtime.runtime.persistence import (
    AtomicFilesystemArtifactPayloadStore,
)
from bijux_canon_runtime.runtime.recovery import (
    RecoveryStepDisposition,
    RuntimeRecoveryError,
    RuntimeRecoveryService,
)


@dataclass(frozen=True, slots=True)
class _SuccessfulAdapter:
    operation: DagOperation
    adapter_id: str = "test:recovery"
    adapter_version: str = "1"

    def execute(
        self,
        step: ConcreteDagStep,
        upstream: tuple[StepOutputArtifact, ...],
        context: StepDispatchContext,
    ) -> tuple[StepOutputArtifact, ...]:
        context.raise_if_stopped()
        dependencies = resolved_input_artifact_ids(step, upstream)
        return tuple(
            StepOutputArtifact.from_payload(
                step=step,
                contract_id=contract_id,
                media_type="application/json",
                payload=json.dumps(
                    {
                        "operation": step.operation.value,
                        "recovered": True,
                    },
                    sort_keys=True,
                ).encode(),
                dependency_artifact_ids=dependencies,
            )
            for contract_id in step.output_artifact_contract_ids
        )


def _index_plan(corpus_id: ArtifactID) -> RuntimeRequestPlan:
    return RuntimeRequestPlanner().plan(
        RuntimeOperationRequest(
            request_id=RequestID("request-interrupted-index"),
            operation=RuntimeRequestOperation.INDEX_BUILD,
            execution_profile=ExecutionProfile.LOCAL_HYBRID_EXACT,
            budget=RuntimeRequestBudget(30.0, 10_000_000),
            replay_mode=ReplayMode.STRICT,
            scope="recovery-test",
            corpus_id=corpus_id,
        )
    )


def _initial_attempt(plan: RuntimeRequestPlan) -> ExecutionAttemptIdentity:
    run = SemanticRunIdentity.derive(
        SemanticRunInputs(
            operation=plan.request_operation,
            scope="recovery-test",
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
        process_id="interrupted-process",
    )


def _persist_failed_attempt(
    root: Path,
) -> tuple[
    AtomicFilesystemArtifactPayloadStore,
    ExecutionAttemptIdentity,
    tuple[StepOutputArtifact, ...],
]:
    store = AtomicFilesystemArtifactPayloadStore(root)
    corpus = AddressedArtifact.from_json(
        {
            "documents": ["ancient-genome-evidence"],
            "schema_version": "bijux.canon.ingest.corpus-snapshot.v1",
        },
        schema_id="ingest.corpus-snapshot.v1",
        producer="test:recovery-source",
    )
    store.put(corpus)
    plan = _index_plan(corpus.descriptor.artifact_id)
    attempt = _initial_attempt(plan)
    ledger = RuntimeEventLedger(store=store, plan=plan, attempt=attempt)
    steps = {step.operation: step for step in plan.steps}
    for step in plan.steps:
        ledger.record(step=step, event_kind=RuntimeEventKind.PLANNED)

    embed = steps[DagOperation.EMBED]
    ledger.record(step=embed, event_kind=RuntimeEventKind.STARTED)
    embed_outputs = _SuccessfulAdapter(DagOperation.EMBED).execute(
        embed,
        (),
        StepDispatchContext(),
    )
    ledger.record(
        step=embed,
        event_kind=RuntimeEventKind.COMPLETED,
        outputs=embed_outputs,
        duration_ms=4.0,
    )

    lexical = steps[DagOperation.LEXICAL_INDEX]
    ledger.record(step=lexical, event_kind=RuntimeEventKind.STARTED)
    ledger.record(
        step=lexical,
        event_kind=RuntimeEventKind.FAILED,
        duration_ms=2.0,
        error=RuntimeError("worker exited after durable start"),
    )

    dense = steps[DagOperation.DENSE_INDEX]
    ledger.record(
        step=dense,
        event_kind=RuntimeEventKind.SKIPPED,
        duration_ms=0.0,
        error=SchedulerError("dependency did not succeed: lexical_index"),
    )
    return store, attempt, embed_outputs


def test_recovery_requires_reconciler_for_started_work(tmp_path: Path) -> None:
    store, attempt, _ = _persist_failed_attempt(tmp_path / "artifacts")
    service = RuntimeRecoveryService(store)

    with pytest.raises(
        RuntimeRecoveryError,
        match="started operations require reconcilers: lexical-index",
    ):
        service.recover(
            run_id=str(attempt.run_id),
            source_attempt_id=attempt.attempt_id,
            request_id=RequestID("request-recovery-without-reconciler"),
            process_id="recovery-process",
            live_adapters={
                DagOperation.DENSE_INDEX: _SuccessfulAdapter(DagOperation.DENSE_INDEX)
            },
        )

    inspection = RuntimeRunInspector(store).inspect(str(attempt.run_id))
    assert inspection.status is InspectedRunStatus.FAILED
    assert len(inspection.attempts) == 1


def test_recovery_reuses_reconciles_and_executes_exact_boundaries(
    tmp_path: Path,
) -> None:
    store, attempt, embed_outputs = _persist_failed_attempt(tmp_path / "artifacts")
    service = RuntimeRecoveryService(store)
    request_id = RequestID("request-recovery-success")
    arguments = {
        "run_id": str(attempt.run_id),
        "source_attempt_id": attempt.attempt_id,
        "request_id": request_id,
        "process_id": "recovery-process",
        "live_adapters": {
            DagOperation.DENSE_INDEX: _SuccessfulAdapter(DagOperation.DENSE_INDEX)
        },
        "reconciliation_adapters": {
            DagOperation.LEXICAL_INDEX: _SuccessfulAdapter(DagOperation.LEXICAL_INDEX)
        },
    }

    recovered = service.recover(**arguments)

    assert recovered.source.status is InspectedRunStatus.FAILED
    assert recovered.recovery.status is InspectedRunStatus.COMPLETED
    assert recovered.reused is False
    assert recovered.recovery.selected_attempt_id != attempt.attempt_id
    assert recovered.recovery.attempts[-1].source_attempt_id == attempt.attempt_id
    assert recovered.recovery.failures == ()
    assert {step.step_id: step.disposition for step in recovered.steps} == {
        "embed": RecoveryStepDisposition.REUSED,
        "lexical_index": RecoveryStepDisposition.RECONCILED,
        "dense_index": RecoveryStepDisposition.EXECUTED,
    }
    embed = next(step for step in recovered.steps if step.step_id == "embed")
    assert embed.source_output_artifact_ids == tuple(
        artifact.artifact_id for artifact in embed_outputs
    )
    assert embed.recovery_output_artifact_ids == embed.source_output_artifact_ids
    assert recovered.retained_source_artifact_ids
    assert recovered.transition_artifact_ids

    repeated = service.recover(**arguments)

    assert repeated.reused is True
    assert repeated.recovery == recovered.recovery
    assert repeated.transition_artifact_ids == ()
    assert len(repeated.recovery.attempts) == 2


def test_recovery_refuses_to_fork_an_outdated_attempt(tmp_path: Path) -> None:
    store, attempt, _ = _persist_failed_attempt(tmp_path / "artifacts")
    service = RuntimeRecoveryService(store)
    service.recover(
        run_id=str(attempt.run_id),
        source_attempt_id=attempt.attempt_id,
        request_id=RequestID("request-first-recovery"),
        process_id="recovery-process",
        live_adapters={
            DagOperation.DENSE_INDEX: _SuccessfulAdapter(DagOperation.DENSE_INDEX)
        },
        reconciliation_adapters={
            DagOperation.LEXICAL_INDEX: _SuccessfulAdapter(DagOperation.LEXICAL_INDEX)
        },
    )

    with pytest.raises(
        RuntimeRecoveryError,
        match="recovery must supersede the latest attempt",
    ):
        service.recover(
            run_id=str(attempt.run_id),
            source_attempt_id=attempt.attempt_id,
            request_id=RequestID("request-outdated-recovery"),
            process_id="another-process",
            live_adapters={},
            reconciliation_adapters={
                DagOperation.LEXICAL_INDEX: _SuccessfulAdapter(
                    DagOperation.LEXICAL_INDEX
                )
            },
        )
