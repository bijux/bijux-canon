# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import pytest

from bijux_canon_index.application import (
    CONTENT_EVIDENCE_RETRIEVAL_POLICY_ID,
    CONTENT_EVIDENCE_RETRIEVAL_POLICY_V1_ID,
    LEGACY_RETRIEVAL_POLICY_ID,
    resolve_hybrid_retrieval_policy,
)


def test_content_evidence_policy_admits_symmetric_deep_candidates() -> None:
    policy = resolve_hybrid_retrieval_policy(CONTENT_EVIDENCE_RETRIEVAL_POLICY_ID)

    assert policy.candidate_limit(10) == 500
    assert policy.lexical_limit(10) == 500
    assert policy.fusion_policy(top_k=10).top_k == 500
    assert policy.fusion_policy(top_k=10).dense_weight == 2.0
    assert policy.fallback_to_exact_on_ann_refusal is True
    assert policy.uses_evidence_planning is True
    assert policy.maximum_dense_attempts == 2
    vex_budget = policy.vex_budget(max_latency_ms=500.0, max_candidates=500)
    assert vex_budget.minimum_recall == 0.9
    assert vex_budget.require_witness is True
    assert vex_budget.max_memory_bytes == 512 * 1024 * 1024
    assert policy.record(top_k=10)["identity_sha256"] == policy.identity_sha256
    assert policy.record(top_k=10)["evidence_planning"] == {
        "max_subqueries": 8,
        "per_query_top_k": "candidate_limit",
        "planning_policy_id": "bijux.canon.index.evidence-planning.content-v1",
        "top_k": "requested_top_k",
    }


def test_previous_content_policy_remains_resolvable_without_behavior_drift() -> None:
    policy = resolve_hybrid_retrieval_policy(
        CONTENT_EVIDENCE_RETRIEVAL_POLICY_V1_ID
    )

    assert policy.uses_evidence_planning is False
    assert "evidence_planning" not in policy.record(top_k=10)


def test_legacy_policy_retains_the_observed_asymmetric_boundary() -> None:
    policy = resolve_hybrid_retrieval_policy(LEGACY_RETRIEVAL_POLICY_ID)

    assert policy.candidate_limit(10) == 40
    assert policy.lexical_limit(10) == 10
    assert policy.fallback_to_exact_on_ann_refusal is False
    assert policy.maximum_dense_attempts == 1


def test_unknown_retrieval_policy_is_rejected() -> None:
    with pytest.raises(ValueError, match="unsupported hybrid retrieval policy"):
        resolve_hybrid_retrieval_policy("unknown")
