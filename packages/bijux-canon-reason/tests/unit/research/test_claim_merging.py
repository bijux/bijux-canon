# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Research claim canonicalization and dependency tests."""

from __future__ import annotations

import pytest

from bijux_canon_reason.research import (
    ClaimMergeError,
    ClaimMergeErrorCode,
    ClaimMergeResult,
    ClaimMergingService,
    MergeableClaim,
    create_mergeable_claim,
)


def _artifact(value: str) -> str:
    return "sha256:" + value * 64


def _claim(
    claim_id: str,
    semantic_key: str,
    statement: str,
    *,
    scope: str = "a",
    qualifiers: tuple[tuple[str, str], ...] = (),
    evidence: tuple[str, ...] = ("1",),
    parents: tuple[str, ...] = (),
) -> MergeableClaim:
    return create_mergeable_claim(
        claim_artifact_id=_artifact(claim_id),
        semantic_key=semantic_key,
        statement=statement,
        scope_artifact_id=_artifact(scope),
        qualifiers=qualifiers,
        evidence_artifact_ids=tuple(_artifact(item) for item in evidence),
        derived_from_claim_artifact_ids=tuple(_artifact(item) for item in parents),
    )


def test_merges_explicit_equivalence_and_retains_qualification_variants() -> None:
    first = _claim(
        "a",
        "intervention improves outcome",
        "The intervention improves the outcome.",
    )
    duplicate = _claim(
        "b",
        "intervention improves outcome",
        "Outcome improvement follows the intervention.",
        evidence=("1", "2"),
        parents=("a",),
    )
    qualified = _claim(
        "c",
        "intervention improves outcome",
        "The intervention improves the outcome in adults.",
        qualifiers=(("population", "adults"),),
    )
    dependent = _claim(
        "d",
        "outcome predicts retention",
        "The outcome predicts retention.",
        evidence=("1",),
        parents=("a",),
    )

    result = ClaimMergingService().merge(
        graph_artifact_id=_artifact("e"),
        claims=(dependent, qualified, duplicate, first),
    )
    restarted = ClaimMergeResult.model_validate_json(result.model_dump_json())

    assert restarted == result
    assert len(result.canonical_claims) == 2
    merged = next(
        item
        for item in result.canonical_claims
        if len(item.source_claim_artifact_ids) == 3
    )
    assert len(merged.variants) == 2
    assert merged.unique_support_count == 2
    assert set(merged.source_claim_artifact_ids) == {
        first.claim_artifact_id,
        duplicate.claim_artifact_id,
        qualified.claim_artifact_id,
    }
    assert len(result.dependencies) == 2
    assert {item.internal_to_canonical_claim for item in result.dependencies} == {
        False,
        True,
    }
    assert len(result.shared_evidence) == 1
    assert result.shared_evidence[0].evidence_artifact_id == _artifact("1")
    assert result.raw_evidence_reference_count == 5
    assert result.unique_evidence_artifact_ids == (_artifact("1"), _artifact("2"))
    assert result.prevented_double_count == 3


def test_same_words_without_shared_semantic_key_are_not_merged() -> None:
    first = _claim("a", "finding under method one", "The result is stable.")
    second = _claim("b", "finding under method two", "The result is stable.")

    result = ClaimMergingService().merge(
        graph_artifact_id=_artifact("e"), claims=(first, second)
    )

    assert len(result.canonical_claims) == 2
    assert len(result.mappings) == 2


def test_unsupported_claim_merges_without_inventing_support() -> None:
    unsupported = _claim("a", "unsupported", "An unresolved claim.", evidence=())

    result = ClaimMergingService().merge(
        graph_artifact_id=_artifact("e"), claims=(unsupported,)
    )

    assert result.canonical_claims[0].evidence_artifact_ids == ()
    assert result.canonical_claims[0].unique_support_count == 0
    assert result.raw_evidence_reference_count == 0
    assert result.prevented_double_count == 0


def test_source_dependency_cycle_fails_closed() -> None:
    first = _claim("a", "first", "First claim.", parents=("b",))
    second = _claim("b", "second", "Second claim.", parents=("a",))

    with pytest.raises(ClaimMergeError) as caught:
        ClaimMergingService().merge(
            graph_artifact_id=_artifact("e"), claims=(first, second)
        )

    assert caught.value.code is ClaimMergeErrorCode.source_dependency_cycle


def test_merge_induced_canonical_cycle_fails_closed() -> None:
    first_variant = _claim("a", "first", "First claim.")
    second = _claim("b", "second", "Second claim.", parents=("a",))
    later_first_variant = _claim(
        "c", "first", "First claim in another wording.", parents=("b",)
    )

    with pytest.raises(ClaimMergeError) as caught:
        ClaimMergingService().merge(
            graph_artifact_id=_artifact("e"),
            claims=(first_variant, second, later_first_variant),
        )

    assert caught.value.code is ClaimMergeErrorCode.canonical_dependency_cycle


def test_duplicate_unknown_and_self_dependencies_fail_closed() -> None:
    service = ClaimMergingService()
    claim = _claim("a", "first", "First claim.")
    with pytest.raises(ClaimMergeError) as duplicate:
        service.merge(graph_artifact_id=_artifact("e"), claims=(claim, claim))
    assert duplicate.value.code is ClaimMergeErrorCode.duplicate_claim

    with pytest.raises(ClaimMergeError) as unknown:
        service.merge(
            graph_artifact_id=_artifact("e"),
            claims=(_claim("a", "first", "First claim.", parents=("f",)),),
        )
    assert unknown.value.code is ClaimMergeErrorCode.unknown_dependency

    with pytest.raises(ClaimMergeError) as self_dependency:
        service.merge(
            graph_artifact_id=_artifact("e"),
            claims=(_claim("a", "first", "First claim.", parents=("a",)),),
        )
    assert self_dependency.value.code is ClaimMergeErrorCode.self_dependency
