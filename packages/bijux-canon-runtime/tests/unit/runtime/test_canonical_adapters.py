# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

import os
from pathlib import Path

import pytest

from bijux_canon_ingest.core.types import Chunk
from bijux_canon_ingest.retrieval.indexes import build_bm25_index
from bijux_canon_runtime.model.artifact.artifact import Artifact
from bijux_canon_runtime.application.runtime_configuration import (
    resolve_runtime_configuration,
)
from bijux_canon_runtime.model.artifact.retrieved_evidence import RetrievedEvidence
from bijux_canon_runtime.ontology import (
    ArtifactScope,
    ArtifactType,
    EvidenceDeterminism,
)
from bijux_canon_runtime.ontology.ids import (
    AgentID,
    ArtifactID,
    ContentHash,
    ContractID,
    EvidenceID,
    TenantID,
)
from bijux_canon_runtime.runtime.execution import integration_loaders


def _evidence() -> RetrievedEvidence:
    return RetrievedEvidence(
        spec_version="v1",
        evidence_id=EvidenceID("evidence-1"),
        tenant_id=TenantID("tenant-a"),
        determinism=EvidenceDeterminism.DETERMINISTIC,
        source_uri="document:paper-1",
        content_hash=ContentHash("a" * 64),
        score=0.9,
        vector_contract_id=ContractID("contract-1"),
    )


def test_retrieval_and_contract_adapters_use_canonical_services(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    index_path = tmp_path / "index.msgpack"
    index = build_bm25_index(
        chunks=[
            Chunk(
                doc_id="paper-1",
                text="Ancient DNA supports population continuity.",
                start=0,
                end=43,
                metadata={"title": "Paper One"},
                embedding=(),
            )
        ]
    )
    index.save(str(index_path))
    monkeypatch.setenv("BIJUX_CANON_RUNTIME_RETRIEVAL_INDEX_PATH", str(index_path))
    monkeypatch.setenv("BIJUX_CANON_RUNTIME_WORKING_ROOT", str(tmp_path))
    configuration = resolve_runtime_configuration(environment=dict(os.environ))

    records = integration_loaders.load_retrieval_runner(configuration)(
        query="population continuity",
        top_k=1,
        scope="project",
        vector_contract_id=ContractID("contract-1"),
    )

    assert len(records) == 1
    assert records[0]["content"] == "Ancient DNA supports population continuity."
    assert records[0]["vector_contract_id"] == "contract-1"
    assert integration_loaders.load_vector_contract_enforcer()(
        ContractID("contract-1"), [_evidence()]
    )


def test_retrieval_adapter_uses_passed_configuration_after_environment_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    index_path = tmp_path / "index.msgpack"
    build_bm25_index(
        chunks=[
            Chunk(
                doc_id="paper-1",
                text="Configured retrieval authority.",
                start=0,
                end=31,
                embedding=(),
            )
        ]
    ).save(str(index_path))
    configuration = resolve_runtime_configuration(
        explicit={
            "retrieval_index_path": index_path,
            "working_root": tmp_path / "workspace",
        }
    )
    monkeypatch.setenv(
        "BIJUX_CANON_RUNTIME_RETRIEVAL_INDEX_PATH",
        str(tmp_path / "wrong-index.msgpack"),
    )

    records = integration_loaders.load_retrieval_runner(configuration)(
        query="configured authority",
        top_k=1,
        scope="project",
        vector_contract_id=ContractID("contract-1"),
    )

    assert records[0]["content"] == "Configured retrieval authority."


def test_reason_adapter_executes_canonical_typed_workflow() -> None:
    artifact = Artifact(
        spec_version="v1",
        artifact_id=ArtifactID("artifact-1"),
        tenant_id=TenantID("tenant-a"),
        artifact_type=ArtifactType.AGENT_INVOCATION,
        producer="agent",
        parent_artifacts=(),
        content_hash=ContentHash("b" * 64),
        scope=ArtifactScope.WORKING,
    )

    bundle = integration_loaders.load_reasoning_runner(resolve_runtime_configuration())(
        agent_outputs=[artifact],
        evidence=[_evidence()],
        seed=7,
    )

    assert bundle.spec_version == "v1"
    assert bundle.producer_agent_id == AgentID("bijux-canon-reason:application:run:v1")
    assert bundle.evidence_ids == (EvidenceID("evidence-1"),)


def test_agent_loader_executes_canonical_offline_service(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BIJUX_CANON_RUNTIME_WORKING_ROOT", str(tmp_path))
    records = integration_loaders.load_agent_runner(
        resolve_runtime_configuration(environment=dict(os.environ))
    )(
        agent_id=AgentID("researcher"),
        seed=3,
        inputs_fingerprint="input-fingerprint",
        declared_outputs=(ArtifactType.AGENT_INVOCATION.value,),
        evidence=[_evidence()],
    )

    assert len(records) == 1
    assert records[0]["artifact_type"] == ArtifactType.AGENT_INVOCATION.value
    assert str(records[0]["artifact_id"]).startswith("agent-")
    assert (tmp_path / "artifacts" / "api" / "results").is_dir()
