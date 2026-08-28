# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from dataclasses import replace

import pytest

from bijux_canon_index.application import (
    ExactSearchCandidate,
    ExactSearchWitness,
    VexExecutionBudget,
    VexExecutionObservation,
    VexPolicyMode,
    VexPolicyStatus,
    VexPolicyViolation,
    evaluate_vex_budget,
)


def _witness() -> ExactSearchWitness:
    return ExactSearchWitness(
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
        candidates=(ExactSearchCandidate(1, 1.0, "chunk-a"),),
        candidate_order_sha256="c" * 64,
        result_sha256="d" * 64,
    )


def _budget() -> VexExecutionBudget:
    return VexExecutionBudget(
        max_latency_ms=100.0,
        max_memory_bytes=1_000_000,
        max_candidates=100,
        max_ef_search=128,
        minimum_recall=0.95,
    )


def _observation() -> VexExecutionObservation:
    return VexExecutionObservation(
        latency_ms=100.0,
        memory_bytes=1_000_000,
        candidate_count=100,
        ef_search=128,
        recall_at_k=0.95,
        result_reachability=1.0,
        witness=_witness(),
    )


def test_budget_boundaries_are_admitted() -> None:
    decision = evaluate_vex_budget(_budget(), _observation())

    assert decision.status is VexPolicyStatus.admitted
    assert decision.violations == ()


@pytest.mark.parametrize(
    ("observation", "violation"),
    [
        (
            replace(_observation(), latency_ms=100.1),
            VexPolicyViolation.latency_budget_exceeded,
        ),
        (
            replace(_observation(), memory_bytes=1_000_001),
            VexPolicyViolation.memory_budget_exceeded,
        ),
        (
            replace(_observation(), candidate_count=101),
            VexPolicyViolation.candidate_budget_exceeded,
        ),
        (
            replace(_observation(), ef_search=129),
            VexPolicyViolation.ef_search_budget_exceeded,
        ),
        (
            replace(_observation(), witness=None),
            VexPolicyViolation.witness_required,
        ),
        (
            replace(_observation(), recall_at_k=None),
            VexPolicyViolation.minimum_recall_not_measured,
        ),
        (
            replace(_observation(), recall_at_k=0.94),
            VexPolicyViolation.minimum_recall_not_met,
        ),
        (
            replace(_observation(), result_reachability=0.99),
            VexPolicyViolation.result_unreachable,
        ),
    ],
)
def test_each_budget_violation_has_a_stable_refusal(
    observation: VexExecutionObservation,
    violation: VexPolicyViolation,
) -> None:
    decision = evaluate_vex_budget(_budget(), observation)

    assert decision.status is VexPolicyStatus.refused
    assert violation in decision.violations


def test_report_mode_flags_without_losing_violation_identity() -> None:
    decision = evaluate_vex_budget(
        _budget(),
        replace(_observation(), latency_ms=101.0, recall_at_k=0.9),
        mode=VexPolicyMode.report,
    )

    assert decision.status is VexPolicyStatus.flagged
    assert decision.violations == (
        VexPolicyViolation.latency_budget_exceeded,
        VexPolicyViolation.minimum_recall_not_met,
    )


@pytest.mark.parametrize(
    "budget",
    [
        VexExecutionBudget(1.0, 1, 1, 1, 0.0),
        VexExecutionBudget(1.0, 1, 1, 1, 1.0),
    ],
)
def test_recall_budget_endpoints_are_valid(budget: VexExecutionBudget) -> None:
    assert budget.minimum_recall in {0.0, 1.0}


def test_invalid_budget_is_refused_during_construction() -> None:
    with pytest.raises(ValueError, match="latency"):
        VexExecutionBudget(0.0, 1, 1, 1, 0.9)
    with pytest.raises(ValueError, match="effort"):
        VexExecutionBudget(1.0, 0, 1, 1, 0.9)
    with pytest.raises(ValueError, match="recall"):
        VexExecutionBudget(1.0, 1, 1, 1, 1.1)
