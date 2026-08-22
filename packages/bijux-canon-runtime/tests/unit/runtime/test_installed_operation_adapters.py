# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Tests for installed package adapters at exclusive Runtime DAG boundaries."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("faiss")

from bijux_canon_index.application import IndexGenerationArchive, IndexService
from bijux_canon_index.infra.embeddings.local_model import EmbeddedBatch

from bijux_canon_runtime.application.request_planner import RuntimeRequestPlanner
from bijux_canon_runtime.model.execution.request_plan import (
    ExecutionProfile,
    RuntimeOperationRequest,
    RuntimeRequestBudget,
    RuntimeRequestOperation,
)
from bijux_canon_runtime.ontology.ids import RequestID
from bijux_canon_runtime.ontology.public import ReplayMode
from bijux_canon_runtime.runtime.execution.installed_operation_adapters import (
    CanonicalDenseIndexOperationAdapter,
    CanonicalEmbeddingOperationAdapter,
    CanonicalIngestOperationAdapter,
    CanonicalLexicalIndexOperationAdapter,
    CanonicalSnapshotOperationAdapter,
)
from bijux_canon_runtime.runtime.execution.application_executor import (
    RuntimeFirstExecutionService,
)
from bijux_canon_runtime.runtime.execution.operation_dispatcher import (
    OperationDispatcher,
)
from bijux_canon_runtime.runtime.inspection import RuntimeRunInspector
from bijux_canon_runtime.runtime.persistence import (
    AtomicFilesystemArtifactPayloadStore,
)


class _Embedding:
    model_lock_id = "sha256:" + "b" * 64

    def embed(self, texts: tuple[str, ...]) -> EmbeddedBatch:
        vectors = tuple(
            (1.0, 0.0, 0.0) if index % 2 == 0 else (0.0, 1.0, 0.0)
            for index, _ in enumerate(texts)
        )
        return EmbeddedBatch(vectors, self.model_lock_id, "cpu", 8)


def _budget() -> RuntimeRequestBudget:
    return RuntimeRequestBudget(
        timeout_seconds=30.0,
        max_artifact_bytes=10_000_000,
    )


def test_installed_ingest_and_index_adapters_persist_restartable_payloads(
    tmp_path: Path,
) -> None:
    source = tmp_path / "papers"
    source.mkdir()
    (source / "evidence.md").write_text(
        "# Ancient DNA\n\nAncient genomes preserve direct population evidence.\n",
        encoding="utf-8",
    )
    planner = RuntimeRequestPlanner()
    corpus_request = RuntimeOperationRequest(
        request_id=RequestID("request-corpus"),
        operation=RuntimeRequestOperation.CORPUS_PREPARE,
        execution_profile=ExecutionProfile.LOCAL_HYBRID_ANN,
        budget=_budget(),
        replay_mode=ReplayMode.STRICT,
        scope="local",
        source_directory=str(source),
    )
    corpus_plan = planner.plan(corpus_request)
    corpus_dispatcher = OperationDispatcher(
        (
            CanonicalIngestOperationAdapter(),
            CanonicalSnapshotOperationAdapter(),
        )
    )
    corpus_results = corpus_dispatcher.dispatch_plan(corpus_plan)
    snapshot = corpus_results[-1].artifacts[0]
    store = AtomicFilesystemArtifactPayloadStore(tmp_path / "runtime" / "cas")
    store.put(snapshot.artifact)

    corpus_execution = RuntimeFirstExecutionService(
        store=store,
        dispatcher=corpus_dispatcher,
        process_id="installed-adapter-test",
        max_workers=2,
    ).execute(corpus_request, lambda: False)
    corpus_inspection = RuntimeRunInspector(store).inspect(
        str(corpus_execution["run_id"])
    )
    assert corpus_inspection.status.value == "completed"
    assert corpus_inspection.terminal_step_ids == ("snapshot",)

    index_request = RuntimeOperationRequest(
        request_id=RequestID("request-index"),
        operation=RuntimeRequestOperation.INDEX_BUILD,
        execution_profile=ExecutionProfile.LOCAL_HYBRID_ANN,
        budget=_budget(),
        replay_mode=ReplayMode.STRICT,
        scope="local",
        corpus_id=snapshot.artifact_id,
    )
    index_plan = planner.plan(index_request)
    index_service = IndexService(tmp_path / "runtime" / "indexes")
    index_dispatcher = OperationDispatcher(
        (
            CanonicalEmbeddingOperationAdapter(
                store=store,
                embedding=_Embedding(),
            ),
            CanonicalLexicalIndexOperationAdapter(
                store=store,
                working_root=tmp_path / "runtime" / "operations",
            ),
            CanonicalDenseIndexOperationAdapter(
                index=index_service,
                working_root=tmp_path / "runtime" / "operations",
            ),
        )
    )
    index_results = index_dispatcher.dispatch_plan(index_plan)

    assert [result.step_id for result in index_results] == [
        "embed",
        "lexical_index",
        "dense_index",
    ]
    assert index_results[0].artifacts[0].artifact.descriptor.dependencies == (
        snapshot.artifact_id,
    )
    assert index_results[1].artifacts[0].artifact.descriptor.dependencies == (
        snapshot.artifact_id,
    )
    composite = index_results[-1].artifacts[0]
    archive = IndexGenerationArchive.from_bytes(composite.payload)
    assert composite.contract_id == "index.composite.v1"
    assert archive.generation_id == index_service.inspect().generation_id
    assert tuple((tmp_path / "runtime" / "operations").iterdir()) == ()

    store.put(composite.artifact)
    restarted_store = AtomicFilesystemArtifactPayloadStore(store.root)
    assert restarted_store.load(composite.artifact_id) == composite.artifact
    restarted_index = IndexService(tmp_path / "restarted" / "indexes")
    admitted = restarted_index.admit_archive(
        restarted_store.load(composite.artifact_id).canonical_bytes,
        activate=True,
    )
    assert admitted.generation_id == archive.generation_id
    assert restarted_index.verify().integrity.status == "verified"

    execution = RuntimeFirstExecutionService(
        store=store,
        dispatcher=index_dispatcher,
        process_id="installed-adapter-test",
        max_workers=2,
    ).execute(index_request, lambda: False)
    inspection = RuntimeRunInspector(store).inspect(str(execution["run_id"]))
    assert execution["status"] == "completed"
    assert inspection.status.value == "completed"
    assert [step.step_id for step in inspection.steps] == [
        "embed",
        "lexical_index",
        "dense_index",
    ]
