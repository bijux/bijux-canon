# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from bijux_canon_index.application import (
    ExactSearchCandidate,
    ExactSearchWitness,
    VexArtifactStore,
    VexCandidateRecord,
    VexDriftKind,
    VexExecutionArtifact,
    VexPolicyDecision,
    VexPolicyStatus,
    VexReplayInput,
    VexReplayOutcome,
    compare_vex_artifacts,
    replay_vex_execution,
)


def _execution(
    *,
    approximate_score: float = 0.99,
    exact_score: float = 1.0,
    request: dict[str, object] | None = None,
    plan: dict[str, object] | None = None,
    vector_sha256: str = "a" * 64,
    latency_ms: float = 1.0,
) -> VexExecutionArtifact:
    request = request or {
        "generation_id": "sha256:generation",
        "model_lock_artifact_id": "sha256:model",
        "filters": {"language": "en"},
        "budget": {"top_k": 1},
    }
    plan = plan or {
        "backend": "faiss-hnsw",
        "backend_version": "1.15.0",
        "algorithm": "hnsw",
        "ef_search": 128,
        "software_locks": {"faiss": "1.15.0"},
        "hardware_class": "cpu-x86_64",
    }
    witness = ExactSearchWitness(
        schema_version="bijux.canon.vex.exact_witness.v1",
        witness_id="sha256:witness",
        generation_id=str(request["generation_id"]),
        model_lock_artifact_id=str(request["model_lock_artifact_id"]),
        backend="faiss-flat-ip",
        backend_version="1.15.0",
        metric="inner_product",
        normalization="l2-float32-v1",
        query_vector_sha256=vector_sha256,
        filter_sha256="b" * 64,
        top_k=1,
        candidates=(ExactSearchCandidate(1, exact_score, "chunk-a"),),
        candidate_order_sha256="c" * 64,
        result_sha256="d" * 64,
    )
    return VexExecutionArtifact(
        request=request,
        normalized_vector_sha256=vector_sha256,
        plan=plan,
        candidates=(
            VexCandidateRecord("faiss-hnsw", 1, approximate_score, "chunk-a"),
        ),
        witness=witness,
        metrics={"latency_ms": latency_ms, "recall_at_k": 1.0},
        decision=VexPolicyDecision(
            "bijux.canon.vex.policy_decision.v1",
            VexPolicyStatus.admitted,
            (),
        ),
        logs=("query admitted", "witness verified"),
    )


def test_replay_persists_both_attempts_and_ignores_runtime_metric_noise(
    tmp_path: Path,
) -> None:
    store = VexArtifactStore(tmp_path / "store")
    original = store.put(_execution())

    def execute(replay_input: VexReplayInput) -> VexExecutionArtifact:
        assert replay_input.normalized_vector_sha256 == "a" * 64
        with pytest.raises(TypeError):
            replay_input.request["generation_id"] = "changed"  # type: ignore[index]
        return _execution(latency_ms=2.0)

    comparison = replay_vex_execution(store, original.artifact_id, execute)

    assert comparison.outcome is VexReplayOutcome.exact_match
    assert comparison.original_artifact_id != comparison.replay_artifact_id
    assert comparison.original_execution_id == comparison.replay_execution_id
    assert store.load(comparison.original_artifact_id) == original
    assert store.load(comparison.replay_artifact_id).record["metrics"] == {
        "latency_ms": 2.0,
        "recall_at_k": 1.0,
    }


def test_comparison_accepts_bounded_score_noise_and_reports_divergence(
    tmp_path: Path,
) -> None:
    store = VexArtifactStore(tmp_path / "store")
    original = store.put(_execution())
    bounded = store.put(_execution(approximate_score=0.9900005, exact_score=1.0000005))
    divergent = store.put(_execution(approximate_score=0.8))

    comparison = compare_vex_artifacts(original, bounded, score_tolerance=1e-6)
    assert comparison.outcome is VexReplayOutcome.within_tolerance
    assert comparison.maximum_score_delta == pytest.approx(5e-7)
    assert comparison.approximate_candidate_recall == 1.0
    assert comparison.exact_candidate_recall == 1.0
    assert compare_vex_artifacts(original, divergent).outcome is VexReplayOutcome.diverged


@pytest.mark.parametrize(
    ("changed", "expected"),
    [
        ({"vector_sha256": "f" * 64}, VexDriftKind.query_vector),
        ({"request": {"generation_id": "sha256:other"}}, VexDriftKind.generation),
        ({"request": {"model_lock_artifact_id": "sha256:other"}}, VexDriftKind.model),
        ({"request": {"filters": {"language": "sv"}}}, VexDriftKind.filter),
        ({"request": {"budget": {"top_k": 2}}}, VexDriftKind.budget),
        ({"plan": {"backend_version": "2.0.0"}}, VexDriftKind.backend),
        ({"plan": {"software_locks": {"faiss": "2.0.0"}}}, VexDriftKind.software),
        ({"plan": {"hardware_class": "cpu-arm64"}}, VexDriftKind.hardware),
        ({"request": {"top_k": 2}}, VexDriftKind.request),
        ({"plan": {"ef_search": 64}}, VexDriftKind.plan),
    ],
)
def test_comparison_refuses_each_immutable_identity_drift(
    tmp_path: Path,
    changed: dict[str, object],
    expected: VexDriftKind,
) -> None:
    base = _execution()
    request = dict(base.request)
    request.update(changed.get("request", {}))  # type: ignore[arg-type]
    plan = dict(base.plan)
    plan.update(changed.get("plan", {}))  # type: ignore[arg-type]
    replay = _execution(
        request=request,
        plan=plan,
        vector_sha256=str(changed.get("vector_sha256", "a" * 64)),
    )
    store = VexArtifactStore(tmp_path / "store")

    comparison = compare_vex_artifacts(store.put(base), store.put(replay))

    assert comparison.outcome is VexReplayOutcome.refused
    assert expected in comparison.drifts


def test_execution_identity_binds_normalized_vector() -> None:
    original = _execution()
    changed = replace(original, normalized_vector_sha256="f" * 64)

    assert original.execution_id != changed.execution_id


def test_comparison_refuses_witness_identity_drift(tmp_path: Path) -> None:
    original = _execution()
    changed = replace(
        original,
        witness=replace(original.witness, backend_version="2.0.0"),
    )
    store = VexArtifactStore(tmp_path / "store")

    comparison = compare_vex_artifacts(store.put(original), store.put(changed))

    assert comparison.outcome is VexReplayOutcome.refused
    assert comparison.drifts == (VexDriftKind.backend,)


def test_comparison_rejects_invalid_tolerance(tmp_path: Path) -> None:
    stored = VexArtifactStore(tmp_path / "store").put(_execution())
    with pytest.raises(ValueError, match="finite and non-negative"):
        compare_vex_artifacts(stored, stored, score_tolerance=float("nan"))
