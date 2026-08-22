# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Tests for immutable, restart-safe Runtime run publication receipts."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from bijux_canon_runtime.application.request_planner import RuntimeRequestPlanner
from bijux_canon_runtime.model.artifact import AddressedArtifact
from bijux_canon_runtime.model.execution.request_plan import (
    ConcreteDagStep,
    DagOperation,
    ExecutionProfile,
    RuntimeOperationRequest,
    RuntimeRequestBudget,
    RuntimeRequestOperation,
)
from bijux_canon_runtime.ontology.ids import ArtifactID, RequestID
from bijux_canon_runtime.ontology.public import ReplayMode
from bijux_canon_runtime.runtime.execution.application_executor import (
    RuntimeFirstExecutionService,
)
from bijux_canon_runtime.runtime.execution.operation_dispatcher import (
    OperationDispatcher,
    StepDispatchContext,
    StepOutputArtifact,
    resolved_input_artifact_ids,
)
from bijux_canon_runtime.runtime.persistence import (
    AtomicFilesystemArtifactPayloadStore,
)
from bijux_canon_runtime.runtime.publication import (
    ReplayPublicationDisposition,
    ReplayPublicationStatus,
    RunPublicationBindings,
    RuntimeRunReceiptPublisher,
)


@dataclass(frozen=True, slots=True)
class _SuccessfulAdapter:
    operation: DagOperation

    @property
    def adapter_id(self) -> str:
        return f"test:publication:{self.operation.value}"

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
        return tuple(
            StepOutputArtifact.from_payload(
                step=step,
                contract_id=contract_id,
                media_type="application/json",
                payload=json.dumps(
                    {
                        "operation": step.operation.value,
                        "schema_version": contract_id,
                    },
                    sort_keys=True,
                ).encode(),
                dependency_artifact_ids=resolved_input_artifact_ids(step, upstream),
            )
            for contract_id in step.output_artifact_contract_ids
        )


def _completed_run(
    root: Path,
) -> tuple[
    AtomicFilesystemArtifactPayloadStore,
    dict[str, object],
    RunPublicationBindings,
]:
    store = AtomicFilesystemArtifactPayloadStore(root)
    corpus = AddressedArtifact.from_json(
        {
            "documents": ["durable publication evidence"],
            "schema_version": "bijux.canon.ingest.corpus-snapshot.v1",
        },
        schema_id="ingest.corpus-snapshot.v1",
        producer="test:publication-source",
    )
    store.put(corpus)
    request = RuntimeOperationRequest(
        request_id=RequestID("request-publication"),
        operation=RuntimeRequestOperation.INDEX_BUILD,
        execution_profile=ExecutionProfile.LOCAL_HYBRID_EXACT,
        budget=RuntimeRequestBudget(30.0, 10_000_000),
        replay_mode=ReplayMode.STRICT,
        scope="publication-test",
        corpus_id=corpus.descriptor.artifact_id,
    )
    execution = dict(
        RuntimeFirstExecutionService(
            store=store,
            dispatcher=OperationDispatcher(
                tuple(
                    _SuccessfulAdapter(step.operation)
                    for step in RuntimeRequestPlanner().plan(request).steps
                )
            ),
            process_id="publication-test",
            max_workers=2,
        ).execute(request, lambda: False)
    )
    bindings = RunPublicationBindings(
        source_commit="a" * 40,
        corpus_artifact_id=corpus.descriptor.artifact_id,
        index_artifact_id=ArtifactID("sha256:" + "b" * 64),
        model_artifact_id=ArtifactID("sha256:" + "c" * 64),
        configuration_artifact_id=ArtifactID("sha256:" + "d" * 64),
    )
    return store, execution, bindings


def _receipt(
    store: AtomicFilesystemArtifactPayloadStore,
    artifact_id: ArtifactID,
) -> dict[str, object]:
    value = json.loads(store.load(artifact_id).canonical_bytes)
    assert isinstance(value, dict)
    return value


def test_completed_run_publication_is_restart_safe_and_path_independent(
    tmp_path: Path,
) -> None:
    store, execution, bindings = _completed_run(tmp_path / "runtime-store")
    arguments = {
        "run_id": str(execution["run_id"]),
        "selected_attempt_id": str(execution["attempt_id"]),
        "bindings": bindings,
        "replay": ReplayPublicationStatus(ReplayPublicationDisposition.NOT_REQUESTED),
        "limitations": ("local execution only",),
    }

    first = RuntimeRunReceiptPublisher(store).publish(**arguments)
    restarted = AtomicFilesystemArtifactPayloadStore(store.root)
    repeated = RuntimeRunReceiptPublisher(restarted).publish(**arguments)
    receipt = _receipt(restarted, first.receipt_artifact_id)

    assert first.reused is False
    assert repeated.reused is True
    assert repeated.receipt_artifact_id == first.receipt_artifact_id
    assert repeated.stable_citation == first.stable_citation
    assert first.selected_attempt_id == execution["attempt_id"]
    assert first.artifact_count > 0
    assert first.check_count > 0
    assert receipt["run_id"] == execution["run_id"]
    assert receipt["request_id"] == "request-publication"
    assert receipt["plan_sha256"] == execution["plan_sha256"]
    assert receipt["selected_attempt"]["attempt_id"] == execution["attempt_id"]
    assert receipt["bindings"] == {
        "configuration_artifact_id": str(bindings.configuration_artifact_id),
        "corpus_artifact_id": str(bindings.corpus_artifact_id),
        "index_artifact_id": str(bindings.index_artifact_id),
        "model_artifact_id": str(bindings.model_artifact_id),
        "source_commit": bindings.source_commit,
    }
    assert receipt["stable_citation"] == first.stable_citation
    assert str(tmp_path) not in json.dumps(receipt, sort_keys=True)


def test_changed_publication_intent_appends_one_linked_revision(
    tmp_path: Path,
) -> None:
    store, execution, bindings = _completed_run(tmp_path / "runtime-store")
    publisher = RuntimeRunReceiptPublisher(store)
    common = {
        "run_id": str(execution["run_id"]),
        "selected_attempt_id": str(execution["attempt_id"]),
        "bindings": bindings,
        "replay": ReplayPublicationStatus(ReplayPublicationDisposition.NOT_REQUESTED),
    }

    first = publisher.publish(**common)
    second = publisher.publish(
        **common,
        limitations=("evaluation corpus is intentionally bounded",),
    )
    repeated = RuntimeRunReceiptPublisher(store).publish(
        **common,
        limitations=("evaluation corpus is intentionally bounded",),
    )
    second_receipt = _receipt(store, second.receipt_artifact_id)

    assert first.revision == 1
    assert second.revision == 2
    assert second.reused is False
    assert repeated.reused is True
    assert repeated.receipt_artifact_id == second.receipt_artifact_id
    assert second_receipt["previous_receipt_artifact_id"] == str(
        first.receipt_artifact_id
    )
    assert second_receipt["limitations"] == [
        "evaluation corpus is intentionally bounded"
    ]
