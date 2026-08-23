# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Tests for installed package adapters at exclusive Runtime DAG boundaries."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
import hashlib
import json
from pathlib import Path

import pytest

pytest.importorskip("faiss")

from bijux_canon_agent.application import (
    InstalledResearchPort,
    InstalledResearchRequest,
    InstalledResearchResult,
    InstalledResearchService,
)
from bijux_canon_index.application import (
    CONTENT_EVIDENCE_RETRIEVAL_POLICY_ID,
    HybridRetrievalPolicy,
    IndexGenerationArchive,
    IndexQueryChannel,
    IndexQueryRequest,
    IndexService,
    VexArtifactStore,
    resolve_hybrid_retrieval_policy,
)
from bijux_canon_index.evaluation import (
    PublicRetrievalEvaluationRequest,
    PublicRetrievalEvaluator,
    PublicRetrievalMode,
    RetrievalExecutionStatus,
    ReviewedRetrievalQrel,
    ReviewedRetrievalQuery,
)
from bijux_canon_index.infra.embeddings.local_model import EmbeddedBatch
from bijux_canon_runtime.application.request_planner import RuntimeRequestPlanner
from bijux_canon_runtime.model.artifact import AddressedArtifact
from bijux_canon_runtime.model.execution.request_plan import (
    DagOperation,
    ExecutionProfile,
    RetrievalFilters,
    RuntimeOperationRequest,
    RuntimeOutputPolicy,
    RuntimeRequestBudget,
    RuntimeRequestOperation,
)
from bijux_canon_runtime.ontology.ids import ArtifactID, RequestID
from bijux_canon_runtime.ontology.public import ReplayMode
from bijux_canon_runtime.runtime.comparison import (
    ComparisonDimension,
    RuntimeComparisonService,
)
from bijux_canon_runtime.runtime.execution.application_executor import (
    RuntimeFirstExecutionService,
)
from bijux_canon_runtime.runtime.execution.installed_agent_adapter import (
    CanonicalAgentOperationAdapter,
)
from bijux_canon_runtime.runtime.execution.installed_operation_adapters import (
    CanonicalDenseIndexOperationAdapter,
    CanonicalEmbeddingOperationAdapter,
    CanonicalIngestOperationAdapter,
    CanonicalLexicalIndexOperationAdapter,
    CanonicalSnapshotOperationAdapter,
    _indexable_chunks,
)
from bijux_canon_runtime.runtime.execution.installed_persistence_adapters import (
    CanonicalPersistenceOperationAdapter,
    CanonicalPublicationOperationAdapter,
)
from bijux_canon_runtime.runtime.execution.installed_reason_adapter import (
    CanonicalReasonOperationAdapter,
)
from bijux_canon_runtime.runtime.execution.installed_retrieval_adapter import (
    CanonicalRetrievalOperationAdapter,
)
from bijux_canon_runtime.runtime.execution.installed_verification_adapter import (
    CanonicalVerificationOperationAdapter,
)
from bijux_canon_runtime.runtime.execution.operation_dispatcher import (
    OperationDispatcher,
    StepDispatchError,
    StepOutputArtifact,
)
from bijux_canon_runtime.runtime.execution.retrieval_evaluation import (
    InstalledRetrievalEvaluationExecutor,
)
from bijux_canon_runtime.runtime.inspection import RuntimeRunInspector
from bijux_canon_runtime.runtime.persistence import (
    AtomicFilesystemArtifactPayloadStore,
)
from bijux_canon_runtime.runtime.replay import (
    ReplayNetworkPolicy,
    ReplayTolerance,
    RuntimeReplayPolicy,
    RuntimeReplayService,
)


class _Embedding:
    model_lock_id = "sha256:" + "b" * 64

    def embed(self, texts: tuple[str, ...]) -> EmbeddedBatch:
        vectors = tuple(
            (1.0, 0.0, 0.0) if index % 2 == 0 else (0.0, 1.0, 0.0)
            for index, _ in enumerate(texts)
        )
        return EmbeddedBatch(vectors, self.model_lock_id, "cpu", 8)


class _UnexpectedEmbedding:
    model_lock_id = "sha256:" + "b" * 64

    def embed(self, texts: tuple[str, ...]) -> EmbeddedBatch:
        del texts
        raise AssertionError("offline lexical retrieval must not embed the query")


@dataclass(frozen=True, slots=True)
class _IndexedRuntime:
    tmp_path: Path
    planner: RuntimeRequestPlanner
    store: AtomicFilesystemArtifactPayloadStore
    index_service: IndexService
    composite: StepOutputArtifact
    retry: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class _GroundedRuntime:
    indexed: _IndexedRuntime
    retrieval_request: RuntimeOperationRequest
    ask_request: RuntimeOperationRequest
    reason_upstream: StepOutputArtifact
    reason_artifact: StepOutputArtifact


def _budget() -> RuntimeRequestBudget:
    return RuntimeRequestBudget(
        timeout_seconds=30.0,
        max_artifact_bytes=10_000_000,
    )


def test_indexable_chunks_omit_empty_jats_section_paths() -> None:
    text = "Ancient DNA evidence"
    snapshot = {
        "documents": [
            {
                "document_id": "sha256:" + "a" * 64,
                "metadata": {
                    "format_id": "jats",
                    "relative_path": "article.xml",
                    "source_content_sha256": "b" * 64,
                },
                "chunks": [
                    {
                        "chunk_id": "sha256:" + "c" * 64,
                        "chunk_index": 0,
                        "normalized_text": text,
                        "normalized_text_sha256": hashlib.sha256(
                            text.encode("utf-8")
                        ).hexdigest(),
                        "section_paths": [[]],
                    }
                ],
            }
        ]
    }

    chunks = _indexable_chunks(snapshot)

    assert chunks[0].metadata["format"] == "jats"
    assert "section" not in chunks[0].metadata


@pytest.mark.parametrize(
    ("publication_date", "governed_date"),
    [("2015", None), ("2015-06", None), ("2015-06-16", "2015-06-16")],
)
def test_indexable_chunks_preserve_partial_publication_dates_without_fabrication(
    publication_date: str,
    governed_date: str | None,
) -> None:
    text = "Ancient DNA evidence"
    snapshot = {
        "documents": [
            {
                "document_id": "sha256:" + "a" * 64,
                "metadata": {
                    "format_id": "jats",
                    "publication_date": publication_date,
                    "relative_path": "article.xml",
                    "source_content_sha256": "b" * 64,
                },
                "chunks": [
                    {
                        "chunk_id": "sha256:" + "c" * 64,
                        "chunk_index": 0,
                        "normalized_text": text,
                        "normalized_text_sha256": hashlib.sha256(
                            text.encode("utf-8")
                        ).hexdigest(),
                    }
                ],
            }
        ]
    }

    metadata = _indexable_chunks(snapshot)[0].metadata

    assert metadata["publication_date"] == publication_date
    assert metadata.get("date") == governed_date


def _build_indexed_runtime(tmp_path: Path) -> _IndexedRuntime:
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
        configuration_identity_sha256="1" * 64,
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

    execution_service = RuntimeFirstExecutionService(
        store=store,
        dispatcher=index_dispatcher,
        process_id="installed-adapter-test",
        configuration_identity_sha256="1" * 64,
        max_workers=2,
    )
    execution = execution_service.execute(index_request, lambda: False)
    inspection = RuntimeRunInspector(store).inspect(str(execution["run_id"]))
    assert execution["status"] == "completed"
    assert inspection.status.value == "completed"
    assert [step.step_id for step in inspection.steps] == [
        "embed",
        "lexical_index",
        "dense_index",
    ]

    retry = execution_service.execute(
        replace(index_request, request_id=RequestID("request-index-retry")),
        lambda: False,
    )
    retried_inspection = RuntimeRunInspector(store).inspect(str(retry["run_id"]))
    assert [attempt.attempt_number for attempt in retried_inspection.attempts] == [1, 2]
    assert retried_inspection.attempts[-1].relation == "retry"
    assert retried_inspection.attempts[-1].source_attempt_id == execution["attempt_id"]

    return _IndexedRuntime(
        tmp_path=tmp_path,
        planner=planner,
        store=store,
        index_service=index_service,
        composite=composite,
        retry=retry,
    )


def _retrieve_and_reason(indexed: _IndexedRuntime) -> _GroundedRuntime:
    tmp_path = indexed.tmp_path
    planner = indexed.planner
    store = indexed.store
    index_service = indexed.index_service
    composite = indexed.composite

    retrieval_request = RuntimeOperationRequest(
        request_id=RequestID("request-retrieve"),
        operation=RuntimeRequestOperation.RETRIEVE,
        execution_profile=ExecutionProfile.LOCAL_HYBRID_ANN,
        budget=_budget(),
        replay_mode=ReplayMode.STRICT,
        scope="local",
        query="What evidence do ancient genomes preserve?",
        index_id=composite.artifact_id,
        top_k=1,
    )
    retrieval = RuntimeFirstExecutionService(
        store=store,
        dispatcher=OperationDispatcher(
            (
                CanonicalRetrievalOperationAdapter(
                    store=store,
                    index=index_service,
                    embedding=_Embedding(),
                    vex_store_root=tmp_path / "runtime" / "vex",
                ),
            )
        ),
        process_id="installed-retrieval-test",
        configuration_identity_sha256="1" * 64,
    ).execute(retrieval_request, lambda: False)
    terminal_ids = retrieval["terminal_artifact_ids"]
    assert isinstance(terminal_ids, list) and len(terminal_ids) == 1
    evidence_artifact = store.load(ArtifactID(terminal_ids[0]))
    evidence = json.loads(evidence_artifact.canonical_bytes)
    assert evidence["status"] == "success"
    assert evidence["retrieval_mode"] == "local-hybrid-ann"
    assert evidence["resource_reuse"]["archive_status"] == "cold"
    assert evidence["resource_reuse"]["generation"]["load_count"] == 1
    assert evidence["resource_reuse"]["generation"]["miss_count"] == 1
    assert evidence["resource_reuse"]["generation"]["hit_count"] >= 4
    assert evidence["vex_execution"]["decision"]["status"] == "admitted"
    assert len(evidence["hits"]) == 1
    hit = evidence["hits"][0]
    assert hit["verbatim_text"].startswith("# Ancient DNA")
    assert (
        hit["content_sha256"]
        == hashlib.sha256(hit["verbatim_text"].encode("utf-8")).hexdigest()
    )
    assert len(hit["source"]["source_content_sha256"]) == 64
    assert hit["mapping_ids"]
    assert hit["channels"]
    assert hit["locator_segments"]
    assert hit["locator_scope"] == "first-segment-only"
    assert all(
        segment["locator"]["scheme"] == "markdown-line-span"
        for segment in hit["locator_segments"]
    )
    assert all(
        segment["content_sha256"]
        == hashlib.sha256(segment["verbatim_text"].encode()).hexdigest()
        for segment in hit["locator_segments"]
    )

    ask_request = RuntimeOperationRequest(
        request_id=RequestID("request-ask"),
        operation=RuntimeRequestOperation.ASK,
        execution_profile=ExecutionProfile.LOCAL_HYBRID_ANN,
        budget=_budget(),
        replay_mode=ReplayMode.STRICT,
        scope="local",
        query="What evidence do ancient genomes preserve?",
        index_id=composite.artifact_id,
        top_k=1,
        provider="local-recorded",
        output_policy=RuntimeOutputPolicy(
            require_citations=True,
            permit_insufficient_answer=True,
            publish=True,
        ),
    )
    reason_step = next(
        step
        for step in planner.plan(ask_request).steps
        if step.operation is DagOperation.REASON
    )
    reason_upstream = StepOutputArtifact(
        contract_id="index.evidence-set.v1",
        producer_step_id="retrieve",
        producer_operation=DagOperation.RETRIEVE,
        artifact=evidence_artifact,
    )
    reason = OperationDispatcher((CanonicalReasonOperationAdapter(),)).dispatch(
        reason_step,
        (reason_upstream,),
    )
    claim_graph = json.loads(reason.artifacts[0].payload)
    assert claim_graph["status"] == "answered"
    assert "Ancient genomes preserve" in claim_graph["answer"]
    assert "Answer:" in claim_graph["answer"]
    assert "reports: “" not in claim_graph["answer"]
    segment_hashes = {
        segment["verbatim_text"]: segment["content_sha256"]
        for segment in hit["locator_segments"]
    }
    selected_text = claim_graph["evidence_packet"]["selected"][0]["exact_text"]
    assert selected_text in segment_hashes
    for link in claim_graph["citations"]["links"]:
        assert link["exact_text"] in segment_hashes
        assert link["exact_text_sha256"] == segment_hashes[link["exact_text"]]
        assert link["locator_scheme"] == "markdown-line-span"
    assert claim_graph["citation_verification"]["integrity_verified_links"] == len(
        claim_graph["citations"]["links"]
    )
    assert claim_graph["citation_verification"]["integrity_verified_links"] == len(
        hit["locator_segments"]
    )

    return _GroundedRuntime(
        indexed=indexed,
        retrieval_request=retrieval_request,
        ask_request=ask_request,
        reason_upstream=reason_upstream,
        reason_artifact=reason.artifacts[0],
    )


def _retrieval_evidence(
    indexed: _IndexedRuntime,
    *,
    policy: HybridRetrievalPolicy,
    request_id: str,
    vex_root: Path,
) -> dict[str, object]:
    request = RuntimeOperationRequest(
        request_id=RequestID(request_id),
        operation=RuntimeRequestOperation.RETRIEVE,
        execution_profile=ExecutionProfile.LOCAL_HYBRID_ANN,
        budget=_budget(),
        replay_mode=ReplayMode.STRICT,
        scope="local",
        query="What evidence do ancient genomes preserve?",
        index_id=indexed.composite.artifact_id,
        top_k=1,
    )
    result = OperationDispatcher(
        (
            CanonicalRetrievalOperationAdapter(
                store=indexed.store,
                index=indexed.index_service,
                embedding=_Embedding(),
                vex_store_root=vex_root,
                policy=policy,
            ),
        )
    ).dispatch_plan(indexed.planner.plan(request))[-1]
    parsed = json.loads(result.artifacts[0].payload)
    assert isinstance(parsed, dict)
    return parsed


def test_witnessed_ann_refusal_uses_one_bounded_exact_fallback(
    tmp_path: Path,
) -> None:
    indexed = _build_indexed_runtime(tmp_path)
    policy = replace(
        resolve_hybrid_retrieval_policy(CONTENT_EVIDENCE_RETRIEVAL_POLICY_ID),
        policy_id="bijux.canon.index.hybrid-retrieval.test-bounded-fallback",
        vex_max_ef_search=1,
    )
    vex_root = tmp_path / "runtime" / "vex-bounded-fallback"

    evidence = _retrieval_evidence(
        indexed,
        policy=policy,
        request_id="request-vex-bounded-fallback",
        vex_root=vex_root,
    )

    retrieval = evidence["retrieval"]
    assert isinstance(retrieval, dict)
    attempts = retrieval["vex_attempts"]
    assert isinstance(attempts, list) and len(attempts) == 2
    first = attempts[0]
    final = attempts[1]
    assert isinstance(first, dict) and isinstance(final, dict)
    first_comparison = first["exact_comparison"]
    final_comparison = final["exact_comparison"]
    assert isinstance(first_comparison, dict)
    assert isinstance(final_comparison, dict)
    assert evidence["status"] == "success"
    assert evidence["retrieval_mode"] == "local-hybrid-exact"
    assert retrieval["fallback_action"] == "bounded-exact-after-ann-refusal"
    assert first["mode"] == "dense-ann"
    assert first["outcome"] == "refused"
    assert "ef_search_budget_exceeded" in first["violations"]
    assert final["mode"] == "dense-exact"
    assert final["outcome"] == "success"
    assert final_comparison["recall_at_k"] == 1.0
    assert final_comparison["candidates"]
    dense = retrieval["dense"]
    vex_execution = evidence["vex_execution"]
    assert isinstance(dense, dict) and isinstance(vex_execution, dict)
    assert dense["artifact_id"] == final["artifact_id"]
    assert vex_execution["artifact_id"] == final["artifact_id"]
    assert evidence["refusal"] is None

    first_artifact_id = first["artifact_id"]
    assert isinstance(first_artifact_id, str)
    assert VexArtifactStore(vex_root).load(first_artifact_id).record


def test_exhausted_vex_fallback_returns_run_linkable_typed_refusal(
    tmp_path: Path,
) -> None:
    indexed = _build_indexed_runtime(tmp_path)
    policy = replace(
        resolve_hybrid_retrieval_policy(CONTENT_EVIDENCE_RETRIEVAL_POLICY_ID),
        policy_id="bijux.canon.index.hybrid-retrieval.test-refusal",
        vex_max_memory_bytes=1,
    )
    vex_root = tmp_path / "runtime" / "vex-refusal"

    evidence = _retrieval_evidence(
        indexed,
        policy=policy,
        request_id="request-vex-refusal",
        vex_root=vex_root,
    )

    retrieval = evidence["retrieval"]
    refusal = evidence["refusal"]
    assert isinstance(retrieval, dict)
    assert isinstance(refusal, dict)
    attempts = retrieval["vex_attempts"]
    assert isinstance(attempts, list) and len(attempts) == 2
    assert all(isinstance(attempt, dict) for attempt in attempts)
    typed_attempts = [attempt for attempt in attempts if isinstance(attempt, dict)]
    assert evidence["status"] == "refused"
    assert evidence["hits"] == []
    assert evidence["locator_catalog_id"] is None
    assert retrieval["fusion"] is None
    assert retrieval["rerank"] is None
    assert all(attempt["outcome"] == "refused" for attempt in typed_attempts)
    assert all(
        "memory_budget_exceeded" in attempt["violations"] for attempt in typed_attempts
    )
    assert refusal["code"] == "dense_vex_policy_refused"
    assert refusal["attempt_artifact_ids"] == [
        attempt["artifact_id"] for attempt in typed_attempts
    ]
    assert "exact retrieval profile" in refusal["remediation"]
    vex_execution = evidence["vex_execution"]
    assert isinstance(vex_execution, dict)
    assert vex_execution["artifact_id"] == typed_attempts[-1]["artifact_id"]

    ask_request = RuntimeOperationRequest(
        request_id=RequestID("request-ask-after-vex-refusal"),
        operation=RuntimeRequestOperation.ASK,
        execution_profile=ExecutionProfile.LOCAL_HYBRID_ANN,
        budget=_budget(),
        replay_mode=ReplayMode.STRICT,
        scope="local",
        query="What evidence do ancient genomes preserve?",
        index_id=indexed.composite.artifact_id,
        top_k=1,
        provider="local-recorded",
        output_policy=RuntimeOutputPolicy(
            require_citations=True,
            permit_insufficient_answer=True,
            publish=True,
        ),
    )
    reason_step = next(
        step
        for step in indexed.planner.plan(ask_request).steps
        if step.operation is DagOperation.REASON
    )
    refused_upstream = StepOutputArtifact(
        contract_id="index.evidence-set.v1",
        producer_step_id="retrieve",
        producer_operation=DagOperation.RETRIEVE,
        artifact=AddressedArtifact.from_json(
            evidence,
            schema_id="index.evidence-set.v1",
            producer="bijux-canon-runtime:retrieve",
        ),
    )
    reason_result = OperationDispatcher((CanonicalReasonOperationAdapter(),)).dispatch(
        reason_step,
        (refused_upstream,),
    )
    refused_answer = json.loads(reason_result.artifacts[0].payload)
    assert refused_answer["answer_disposition"] == "abstained"
    assert refused_answer["claims"]["claims"] == []
    assert refused_answer["citations"]["links"] == []
    assert "Ancient genomes preserve" not in refused_answer["answer"]

    query = ReviewedRetrievalQuery(
        query_id="refused-content-question",
        query_text="What evidence do ancient genomes preserve?",
        input_identity_sha256="a" * 64,
        qrels=(
            ReviewedRetrievalQrel(
                qrel_id="refused-content-question::qrel",
                chunk_id="not-returned",
                relevance_grade=3,
                relation="supports",
                qrel_identity_sha256="b" * 64,
            ),
        ),
    )
    request = PublicRetrievalEvaluationRequest.create(
        index_artifact_id=str(indexed.composite.artifact_id),
        split="development",
        mode=PublicRetrievalMode.hybrid_ann,
        queries=(query,),
    )
    execution = RuntimeFirstExecutionService(
        store=indexed.store,
        dispatcher=OperationDispatcher(
            (
                CanonicalRetrievalOperationAdapter(
                    store=indexed.store,
                    index=indexed.index_service,
                    embedding=_Embedding(),
                    vex_store_root=tmp_path / "runtime" / "vex-evaluation-refusal",
                    policy=policy,
                ),
            )
        ),
        process_id="installed-refused-retrieval-evaluation-test",
        configuration_identity_sha256="1" * 64,
    )
    observation = InstalledRetrievalEvaluationExecutor(
        execution=execution,
        store=indexed.store,
        index=indexed.index_service,
    ).execute(request, query)

    assert observation.status is RetrievalExecutionStatus.refused
    assert observation.hits == ()
    assert observation.run_id is not None
    assert observation.attempt_id is not None
    assert observation.vex_artifact_id is not None
    assert observation.policy_action == "refused"
    assert observation.fallback_action == "bounded-exact-after-ann-refusal"
    assert observation.stages is None
    assert observation.failure is not None
    assert "memory_budget_exceeded" in observation.failure
    assert "Remediation:" in observation.failure


def test_policy_without_exact_fallback_refuses_after_one_witnessed_attempt(
    tmp_path: Path,
) -> None:
    indexed = _build_indexed_runtime(tmp_path)
    policy = replace(
        resolve_hybrid_retrieval_policy(CONTENT_EVIDENCE_RETRIEVAL_POLICY_ID),
        policy_id="bijux.canon.index.hybrid-retrieval.test-no-fallback",
        fallback_to_exact_on_ann_refusal=False,
        maximum_dense_attempts=1,
        vex_max_ef_search=1,
    )

    evidence = _retrieval_evidence(
        indexed,
        policy=policy,
        request_id="request-vex-no-fallback",
        vex_root=tmp_path / "runtime" / "vex-no-fallback",
    )

    retrieval = evidence["retrieval"]
    assert isinstance(retrieval, dict)
    attempts = retrieval["vex_attempts"]
    assert isinstance(attempts, list) and len(attempts) == 1
    attempt = attempts[0]
    assert isinstance(attempt, dict)
    assert evidence["status"] == "refused"
    assert evidence["retrieval_mode"] == "local-hybrid-ann"
    assert evidence["hits"] == []
    assert retrieval["fallback_action"] == "none"
    assert attempt["mode"] == "dense-ann"
    assert "ef_search_budget_exceeded" in attempt["violations"]


def _verify_reason_and_agent(grounded: _GroundedRuntime) -> None:
    indexed = grounded.indexed
    tmp_path = indexed.tmp_path
    planner = indexed.planner
    store = indexed.store
    index_service = indexed.index_service
    ask_request = grounded.ask_request
    reason_artifact = grounded.reason_artifact
    claim_graph = json.loads(reason_artifact.payload)

    tampered_claim_graph = dict(claim_graph)
    tampered_claim_graph["answer"] = "An answer that is not bound to the synthesis."
    tampered_reason = StepOutputArtifact(
        contract_id="reason.claim-graph.v1",
        producer_step_id="reason",
        producer_operation=DagOperation.REASON,
        artifact=AddressedArtifact.from_json(
            tampered_claim_graph,
            schema_id="reason.claim-graph.v1",
            producer="bijux-canon-runtime:reason",
            dependencies=reason_artifact.artifact.descriptor.dependencies,
        ),
    )
    verification_step = next(
        step
        for step in planner.plan(ask_request).steps
        if step.operation is DagOperation.VERIFY
    )
    with pytest.raises(StepDispatchError, match="differs from its admission"):
        OperationDispatcher((CanonicalVerificationOperationAdapter(),)).dispatch(
            verification_step,
            (tampered_reason,),
        )

    research_request = replace(
        ask_request,
        request_id=RequestID("request-research"),
        operation=RuntimeRequestOperation.RESEARCH,
    )
    agent_step = next(
        step
        for step in planner.plan(research_request).steps
        if step.operation is DagOperation.AGENT
    )
    agent_upstream = StepOutputArtifact(
        contract_id="reason.claim-graph.v1",
        producer_step_id="reason",
        producer_operation=DagOperation.REASON,
        artifact=reason_artifact.artifact,
    )
    research = OperationDispatcher(
        (
            CanonicalAgentOperationAdapter(
                store=store,
                index=index_service,
                embedding=_Embedding(),
                vex_store_root=tmp_path / "runtime" / "vex",
            ),
        )
    ).dispatch(agent_step, (agent_upstream,))
    research_trace = json.loads(research.artifacts[0].payload)
    assert research_trace["status"] == "abstained"
    assert research_trace["convergence_status"] == "insufficient"
    assert research_trace["research_outcome"]["kind"] == "abstained"
    assert research_trace["research_outcome"]["remaining_work"][
        "unsatisfied_requirement_artifact_ids"
    ]
    assert research_trace["termination"]["stop"] is True
    assert research_trace["termination"]["reasons"] == ["explicit_insufficiency"]
    assert research_trace["counterevidence_plan"]["requests"]
    targeted_search = research_trace["targeted_search_plan"]
    assert targeted_search["attempt"]["intent"] == "opposition"
    assert targeted_search["attempt"]["trigger"] == "initial_gap"
    assert (
        targeted_search["attempt"]["requirement_artifact_id"]
        in (
            research_trace["answer_requirement_plan"]["search_requirement_artifact_ids"]
        )
        or targeted_search["attempt"]["source_requirement_artifact_id"]
        in (
            research_trace["answer_requirement_plan"]["search_requirement_artifact_ids"]
        )
    )
    assert research_trace["counterevidence_plan"]["requests"][0][
        "query_text"
    ].startswith(targeted_search["attempt"]["query_text"])
    assert (
        "contradictory evidence"
        in research_trace["counterevidence_plan"]["requests"][0]["query_text"]
    )
    assert research_trace["counterevidence_run"]["records"][0]["outcome"] == (
        "candidate_evidence_found"
    )
    assert research_trace["opposition_candidates"]
    assert (
        research_trace["research_candidates"] == research_trace["opposition_candidates"]
    )
    adjudications = research_trace["candidate_adjudications"]
    classifications = research_trace["candidate_classifications"]
    assert adjudications
    assert classifications
    assert {
        artifact_id
        for report in adjudications
        for artifact_id in report["input_evidence_artifact_ids"]
    } == set(research_trace["research_candidates"])
    assert {
        item["artifact_id"]
        for report in adjudications
        for item in report["classifications"]
    } == {item["artifact_id"] for item in classifications}
    assert all(item["locator_artifact_id"] for item in classifications)
    assert all(len(item["exact_text_sha256"]) == 64 for item in classifications)
    counterevidence_ids = research_trace["counterevidence_retrieval_artifact_ids"]
    assert counterevidence_ids
    assert len(counterevidence_ids) == len(set(counterevidence_ids))
    assert "require relation classification" in research_trace["insufficiencies"][0]
    assert [event["role"] for event in research_trace["causal_events"]] == [
        "plan",
        "researcher",
        "skeptic",
        "adjudicator",
        "verifier",
    ]
    assert research_trace["research_state"]["question"] == (
        "What evidence do ancient genomes preserve?"
    )
    assert research_trace["research_state"]["terminal_status"] == "insufficient"
    assert research_trace["research_state"]["search_budget"] == {
        "limit": 2,
        "used": 1,
    }
    assert len(research_trace["targeted_search_plans"]) == 1
    assert len(research_trace["targeted_search_observations"]) == 1
    assert research_trace["targeted_search_observations"][0]["outcome"] == (
        "material_candidate"
    )
    assert len(research_trace["counterevidence_plans"]) == 1
    assert len(research_trace["counterevidence_runs"]) == 1
    assert research_trace["research_state"]["gaps"]
    requirement_plan = research_trace["answer_requirement_plan"]
    assert requirement_plan["question"] == (
        "What evidence do ancient genomes preserve?"
    )
    assert requirement_plan["outcome"] == "search_required"
    requirement_kinds = {item["kind"] for item in requirement_plan["requirements"]}
    assert requirement_kinds >= {
        "answerability",
        "finding",
        "method_context",
        "opposition",
        "limitation",
    }
    assert requirement_plan["search_requirement_artifact_ids"]
    assert (
        research_trace["causal_trace"]["head_artifact_id"]
        == (research_trace["causal_events"][-1]["artifact_id"])
    )
    tampered_trace = json.loads(research.artifacts[0].payload)
    tampered_trace["research_outcome"]["remaining_work"][
        "unsatisfied_requirement_artifact_ids"
    ] = []
    tampered_research = StepOutputArtifact(
        contract_id="agent.research-trace.v1",
        producer_step_id="agent",
        producer_operation=DagOperation.AGENT,
        artifact=AddressedArtifact.from_json(
            tampered_trace,
            schema_id="agent.research-trace.v1",
            producer="bijux-canon-runtime:agent",
            dependencies=research.artifacts[0].artifact.descriptor.dependencies,
        ),
    )
    research_verification_step = next(
        step
        for step in planner.plan(research_request).steps
        if step.operation is DagOperation.VERIFY
    )
    with pytest.raises(StepDispatchError, match="research trace records are invalid"):
        OperationDispatcher((CanonicalVerificationOperationAdapter(),)).dispatch(
            research_verification_step,
            (tampered_research,),
        )


def _verify_linked_runs(grounded: _GroundedRuntime) -> None:
    indexed = grounded.indexed
    tmp_path = indexed.tmp_path
    store = indexed.store
    index_service = indexed.index_service
    ask_request = grounded.ask_request
    research_request = replace(
        ask_request,
        request_id=RequestID("request-research"),
        operation=RuntimeRequestOperation.RESEARCH,
    )

    linked_dispatcher = OperationDispatcher(
        (
            CanonicalRetrievalOperationAdapter(
                store=store,
                index=index_service,
                embedding=_Embedding(),
                vex_store_root=tmp_path / "runtime" / "vex",
            ),
            CanonicalReasonOperationAdapter(),
            CanonicalAgentOperationAdapter(
                store=store,
                index=index_service,
                embedding=_Embedding(),
                vex_store_root=tmp_path / "runtime" / "vex",
            ),
            CanonicalVerificationOperationAdapter(),
            CanonicalPersistenceOperationAdapter(store=store),
            CanonicalPublicationOperationAdapter(),
        )
    )
    linked = RuntimeFirstExecutionService(
        store=store,
        dispatcher=linked_dispatcher,
        process_id="installed-linked-research-test",
        configuration_identity_sha256="1" * 64,
    ).execute(research_request, lambda: False)
    linked_inspection = RuntimeRunInspector(store).inspect(str(linked["run_id"]))
    assert linked["status"] == "completed"
    assert [item.step_id for item in linked_inspection.steps] == [
        "retrieve",
        "reason",
        "agent",
        "verify",
        "persist",
        "publish",
    ]
    linked_terminal_ids = linked["terminal_artifact_ids"]
    assert isinstance(linked_terminal_ids, list) and len(linked_terminal_ids) == 1
    publication = json.loads(
        store.load(ArtifactID(linked_terminal_ids[0])).canonical_bytes
    )
    assert publication["status"] == "published-local"
    manifest_artifact = store.load(ArtifactID(publication["manifest_artifact_id"]))
    manifest = json.loads(manifest_artifact.canonical_bytes)
    assert manifest["status"] == "persisted"
    assert manifest["artifact_count"] >= 10
    assert any(
        item["schema_id"] == "agent.research-trace.v1" for item in manifest["artifacts"]
    )
    assert any(
        item["schema_id"] == "index.evidence-set.v1" for item in manifest["artifacts"]
    )

    linked_ask = RuntimeFirstExecutionService(
        store=store,
        dispatcher=linked_dispatcher,
        process_id="installed-linked-ask-test",
        configuration_identity_sha256="1" * 64,
    ).execute(
        replace(ask_request, request_id=RequestID("request-linked-ask")),
        lambda: False,
    )
    linked_ask_inspection = RuntimeRunInspector(store).inspect(
        str(linked_ask["run_id"])
    )
    assert [item.step_id for item in linked_ask_inspection.steps] == [
        "retrieve",
        "reason",
        "verify",
        "persist",
        "publish",
    ]
    linked_ask_terminal_ids = linked_ask["terminal_artifact_ids"]
    assert isinstance(linked_ask_terminal_ids, list)
    ask_publication = json.loads(
        store.load(ArtifactID(linked_ask_terminal_ids[0])).canonical_bytes
    )
    ask_manifest = json.loads(
        store.load(ArtifactID(ask_publication["manifest_artifact_id"])).canonical_bytes
    )
    assert any(
        item["schema_id"] == "reason.claim-graph.v1"
        for item in ask_manifest["artifacts"]
    )


def _verify_offline_boundaries(grounded: _GroundedRuntime) -> None:
    indexed = grounded.indexed
    tmp_path = indexed.tmp_path
    planner = indexed.planner
    store = indexed.store
    index_service = indexed.index_service
    retrieval_request = grounded.retrieval_request
    ask_request = grounded.ask_request
    reason_step = next(
        step
        for step in planner.plan(ask_request).steps
        if step.operation is DagOperation.REASON
    )
    reason_upstream = grounded.reason_upstream

    offline_request = replace(
        retrieval_request,
        request_id=RequestID("request-retrieve-filtered"),
        execution_profile=ExecutionProfile.OFFLINE_LEXICAL,
        filters=RetrievalFilters(document_ids=("missing-document",)),
    )
    offline_result = OperationDispatcher(
        (
            CanonicalRetrievalOperationAdapter(
                store=store,
                index=index_service,
                embedding=_UnexpectedEmbedding(),
                vex_store_root=tmp_path / "runtime" / "vex",
            ),
        )
    ).dispatch_plan(planner.plan(offline_request))[-1]
    offline = json.loads(offline_result.artifacts[0].payload)
    assert offline["status"] == "insufficient"
    assert offline["retrieval_mode"] == "lexical"
    assert offline["resource_reuse"]["archive_status"] == "warm"
    assert offline["resource_reuse"]["generation"]["load_count"] == 1
    assert offline["hits"] == []
    assert offline["retrieval"]["dense"] is None
    assert offline["vex_execution"] is None

    offline_upstream = StepOutputArtifact(
        contract_id="index.evidence-set.v1",
        producer_step_id="retrieve",
        producer_operation=DagOperation.RETRIEVE,
        artifact=offline_result.artifacts[0].artifact,
    )
    strict_request = replace(
        ask_request,
        request_id=RequestID("request-ask-strict"),
        output_policy=RuntimeOutputPolicy(
            require_citations=True,
            permit_insufficient_answer=False,
            publish=True,
        ),
    )
    strict_step = next(
        step
        for step in planner.plan(strict_request).steps
        if step.operation is DagOperation.REASON
    )
    with pytest.raises(StepDispatchError, match="insufficient evidence"):
        OperationDispatcher((CanonicalReasonOperationAdapter(),)).dispatch(
            strict_step,
            (offline_upstream,),
        )

    external_step = replace(
        reason_step, inputs=replace(reason_step.inputs, provider="remote")
    )
    with pytest.raises(StepDispatchError, match="configured credentials"):
        OperationDispatcher((CanonicalReasonOperationAdapter(),)).dispatch(
            external_step,
            (reason_upstream,),
        )


def _verify_replay(indexed: _IndexedRuntime) -> None:
    store = indexed.store
    retry = indexed.retry

    replay = RuntimeReplayService(store).replay(
        run_id=str(retry["run_id"]),
        source_attempt_id=str(retry["attempt_id"]),
        request_id=RequestID("request-index-replay"),
        process_id="installed-adapter-replay",
        policy=RuntimeReplayPolicy(
            replay_mode=ReplayMode.STRICT,
            network_policy=ReplayNetworkPolicy.RECORDED_ONLY,
            tolerance=ReplayTolerance(
                max_duration_delta_ms=0.0,
                max_duration_ratio=1.0,
            ),
        ),
    )
    assert replay.replay.status.value == "completed"
    assert replay.comparison.exact_artifact_identities is True
    assert replay.comparison.duration_within_tolerance is False
    assert replay.comparison.accepted is True

    comparison_service = RuntimeComparisonService(RuntimeRunInspector(store))
    comparison = comparison_service.compare(
        baseline_run_id=str(retry["run_id"]),
        baseline_attempt_id=str(retry["attempt_id"]),
        candidate_run_id=str(retry["run_id"]),
        candidate_attempt_id=replay.replay.selected_attempt_id,
    )
    repeated = comparison_service.compare(
        baseline_run_id=str(retry["run_id"]),
        baseline_attempt_id=str(retry["attempt_id"]),
        candidate_run_id=str(retry["run_id"]),
        candidate_attempt_id=replay.replay.selected_attempt_id,
    )

    assert comparison.equivalent is True
    assert tuple(item.dimension for item in comparison.differences) == tuple(
        ComparisonDimension
    )
    assert comparison.comparison_sha256 == repeated.comparison_sha256


def test_installed_ingest_and_index_adapters_persist_restartable_payloads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    delegated_requests: list[InstalledResearchRequest] = []
    original_research = InstalledResearchService.research

    def record_agent_delegation(
        self: InstalledResearchService,
        request: InstalledResearchRequest,
        port: InstalledResearchPort,
    ) -> InstalledResearchResult:
        delegated_requests.append(request)
        return original_research(self, request, port)

    monkeypatch.setattr(InstalledResearchService, "research", record_agent_delegation)
    indexed = _build_indexed_runtime(tmp_path)
    grounded = _retrieve_and_reason(indexed)

    _verify_reason_and_agent(grounded)
    assert len(delegated_requests) == 1
    assert delegated_requests[0].claims
    assert delegated_requests[0].question == (
        "What evidence do ancient genomes preserve?"
    )
    assert delegated_requests[0].requirements
    assert delegated_requests[0].requirement_plan_outcome == "search_required"
    assert all(
        requirement.source_requirement_artifact_id is not None
        for requirement in delegated_requests[0].requirements
    )
    assert delegated_requests[0].evidence_relations
    _verify_linked_runs(grounded)
    assert len(delegated_requests) == 2
    _verify_offline_boundaries(grounded)
    _verify_replay(indexed)


def test_public_retrieval_evaluation_executes_the_persistent_installed_path(
    tmp_path: Path,
) -> None:
    indexed = _build_indexed_runtime(tmp_path)
    query_text = "What direct population evidence do ancient genomes preserve?"
    expected = indexed.index_service.query(
        IndexQueryRequest(
            channel=IndexQueryChannel.lexical,
            query_text=query_text,
            top_k=10,
        )
    ).hits[0]
    query = ReviewedRetrievalQuery(
        query_id="content-question",
        query_text=query_text,
        input_identity_sha256="a" * 64,
        qrels=(
            ReviewedRetrievalQrel(
                qrel_id="content-question::qrel",
                chunk_id=expected.chunk_id,
                relevance_grade=3,
                relation="supports",
                qrel_identity_sha256="b" * 64,
            ),
        ),
    )
    request = PublicRetrievalEvaluationRequest.create(
        index_artifact_id=str(indexed.composite.artifact_id),
        split="development",
        mode=PublicRetrievalMode.hybrid_ann,
        queries=(query,),
    )
    execution = RuntimeFirstExecutionService(
        store=indexed.store,
        dispatcher=OperationDispatcher(
            (
                CanonicalRetrievalOperationAdapter(
                    store=indexed.store,
                    index=indexed.index_service,
                    embedding=_Embedding(),
                    vex_store_root=tmp_path / "runtime" / "vex-evaluation",
                    policy=resolve_hybrid_retrieval_policy(
                        CONTENT_EVIDENCE_RETRIEVAL_POLICY_ID
                    ),
                ),
            )
        ),
        process_id="installed-retrieval-evaluation-test",
        configuration_identity_sha256="1" * 64,
    )
    installed = InstalledRetrievalEvaluationExecutor(
        execution=execution,
        store=indexed.store,
        index=indexed.index_service,
    )

    report = PublicRetrievalEvaluator(installed.execute).evaluate(request)

    assert report.query_count == 1
    assert report.qrel_count == 1
    assert report.macro.metric("recall-at-5").value == 1.0
    assert report.macro.metric("mrr-at-10").value == 1.0
    assert report.observations[0].run_id is not None
    assert report.observations[0].vex_artifact_id is not None
    assert report.observations[0].hits[0].chunk_id == expected.chunk_id
    assert report.observations[0].hits[0].locator_segments
    stages = report.observations[0].stages
    assert stages is not None
    assert all(item.output_rank is not None for item in stages.lexical_candidates)
    assert len(stages.lexical_candidates) == len(stages.dense_candidates)
    persisted = RuntimeRunInspector(indexed.store).inspect(
        str(report.observations[0].run_id)
    )
    assert persisted.status.value == "completed"
    assert persisted.hits
