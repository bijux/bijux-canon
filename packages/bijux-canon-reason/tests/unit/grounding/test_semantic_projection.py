# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Conservative evidence projection behavior."""

from __future__ import annotations

import pytest

from bijux_canon_reason.grounding import (
    EvidenceProjectionMethod,
    project_evidence_clause,
    project_evidence_text,
)


def test_result_attribution_is_removed_without_changing_modality() -> None:
    projections = project_evidence_clause(
        "Our results show that yields can remain below 1% in hot regions."
    )

    assert projections[0].statement == ("Yields can remain below 1% in hot regions.")
    assert projections[0].method is EvidenceProjectionMethod.attribution_removed


@pytest.mark.parametrize(
    ("evidence", "expected"),
    [
        (
            "This study shows that ancient RNA can survive under permafrost conditions.",
            "Ancient RNA can survive under permafrost conditions.",
        ),
        (
            "Lastly, we demonstrate that ethanol specimens offer authentic metagenomic data.",
            "Ethanol specimens offer authentic metagenomic data.",
        ),
        (
            "We conclude that genomics from resin organisms is possible, although time limits remain unresolved.",
            "Genomics from resin organisms is possible, although time limits remain unresolved.",
        ),
    ],
)
def test_scientific_result_attribution_has_reproducible_projection(
    evidence: str, expected: str
) -> None:
    assert project_evidence_clause(evidence)[0].statement == expected


def test_unhedged_indicated_result_is_not_promoted_to_an_asserted_fact() -> None:
    projections = project_evidence_clause(
        "Our results indicate that the treatment improves preservation."
    )

    assert tuple(item.method for item in projections) == (
        EvidenceProjectionMethod.exact_clause,
    )


def test_labeled_enumeration_produces_concise_definition_claims() -> None:
    projections = project_evidence_clause(
        "We sampled two regions: cortical bone (part A), and the dense otic capsule (part C)."
    )

    assert tuple(
        item.statement
        for item in projections
        if item.method is EvidenceProjectionMethod.labeled_definition
    ) == (
        "Part A denotes cortical bone.",
        "Part C denotes the dense otic capsule.",
    )


def test_full_evidence_projection_reproduces_precontrast_claim() -> None:
    projections = project_evidence_text(
        "Our results confirm that recovery can reach 65-fold, while controls remained lower."
    )

    assert any(
        item.statement == "Recovery can reach 65-fold."
        and item.method is EvidenceProjectionMethod.attribution_removed
        for item in projections
    )
