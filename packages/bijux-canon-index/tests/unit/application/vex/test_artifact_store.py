# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

from bijux_canon_index.application import (
    ExactSearchCandidate,
    ExactSearchWitness,
    VexArtifactStore,
    VexCandidateRecord,
    VexExecutionArtifact,
    VexPolicyDecision,
    VexPolicyStatus,
)


def _execution(*, score: float = 1.0) -> VexExecutionArtifact:
    witness = ExactSearchWitness(
        schema_version="bijux.canon.vex.exact_witness.v1",
        witness_id="sha256:witness",
        generation_id="sha256:generation",
        model_lock_artifact_id="sha256:model",
        backend="faiss-flat-ip",
        backend_version="1.15.0",
        metric="inner_product",
        normalization="l2-float32-v1",
        query_vector_sha256="a" * 64,
        filter_sha256="b" * 64,
        top_k=1,
        candidates=(ExactSearchCandidate(1, score, "chunk-a"),),
        candidate_order_sha256="c" * 64,
        result_sha256="d" * 64,
    )
    return VexExecutionArtifact(
        request={"generation_id": "sha256:generation", "top_k": 1},
        normalized_vector_sha256="a" * 64,
        plan={"backend": "faiss-hnsw", "ef_search": 128},
        candidates=(VexCandidateRecord("faiss-hnsw", 1, score, "chunk-a"),),
        witness=witness,
        metrics={"latency_ms": 1.0, "recall_at_k": 1.0},
        decision=VexPolicyDecision(
            "bijux.canon.vex.policy_decision.v1",
            VexPolicyStatus.admitted,
            (),
        ),
        logs=("query admitted", "witness verified"),
    )


def test_store_persists_complete_content_addressed_artifact_and_restarts(
    tmp_path: Path,
) -> None:
    artifact = _execution()
    stored = VexArtifactStore(tmp_path / "store").put(artifact)

    assert stored.artifact_id == artifact.artifact_id
    assert stored.record["request"] == artifact.request
    assert stored.record["normalized_vector_sha256"] == "a" * 64
    assert stored.record["plan"] == artifact.plan
    assert stored.record["candidate_order"]
    assert stored.record["witness"]
    assert stored.record["metrics"] == artifact.metrics
    assert stored.record["decision"]
    assert stored.record["logs"] == list(artifact.logs)
    assert set(stored.record["component_hashes"]) == {
        "candidates",
        "decision",
        "logs",
        "metrics",
        "normalized_vector",
        "plan",
        "request",
        "witness",
    }

    restarted = VexArtifactStore(tmp_path / "store")
    assert restarted.load(artifact.artifact_id) == stored
    assert restarted.put(artifact) == stored


def test_changed_attempt_gets_a_new_address_without_overwrite(tmp_path: Path) -> None:
    store = VexArtifactStore(tmp_path / "store")
    first = store.put(_execution())
    second = store.put(_execution(score=0.9))

    assert first.artifact_id != second.artifact_id
    assert store.load(first.artifact_id) == first
    assert store.load(second.artifact_id) == second


def test_store_refuses_tamper_noncanonical_bytes_and_invalid_identity(
    tmp_path: Path,
) -> None:
    store = VexArtifactStore(tmp_path / "store")
    stored = store.put(_execution())
    path = next((tmp_path / "store" / "objects").rglob("*.json"))
    record = json.loads(path.read_text())
    record["metrics"]["recall_at_k"] = 0.5
    path.write_text(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")

    with pytest.raises(ValueError, match="content address"):
        store.load(stored.artifact_id)
    with pytest.raises(ValueError, match="content-addressed"):
        store.load("../escape")


def test_artifact_refuses_incomplete_and_nonfinite_payloads() -> None:
    with pytest.raises(ValueError, match="candidates and logs"):
        replace(_execution(), candidates=())
    with pytest.raises(ValueError, match="JSON"):
        replace(_execution(), metrics={"latency_ms": float("nan")})
