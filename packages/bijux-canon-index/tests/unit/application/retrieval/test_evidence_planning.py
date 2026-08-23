# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from bijux_canon_index.application import (
    SubqueryOrigin,
    plan_evidence_query,
)


def test_explicit_content_facets_create_bounded_independent_evidence_needs() -> None:
    plan = plan_evidence_query(
        "Across permafrost tissue, petrous bone, young resin, and museum snakes, "
        "what evidence and limitations were reported?"
    )

    assert plan.document_breadth == 4
    assert len(plan.facet_subquery_ids) == 4
    facets = [
        item
        for item in plan.multi_query.subqueries
        if item.subquery_id in plan.facet_subquery_ids
    ]
    assert [item.text for item in facets] == [
        "permafrost tissue evidence result limitation",
        "petrous bone evidence result limitation",
        "young resin evidence result limitation",
        "museum snakes evidence result limitation",
    ]
    assert all(
        item.origin is SubqueryOrigin.generated_evidence_need for item in facets
    )
    assert len(plan.multi_query.subqueries) <= 8


def test_skeptical_question_plans_counterevidence_without_domain_identities() -> None:
    plan = plan_evidence_query(
        "Does observed damage prove that every recovered sequence is ancient?"
    )

    assert plan.document_breadth == 3
    counterevidence = next(
        item
        for item in plan.multi_query.subqueries
        if "counterevidence" in item.derivation
    )
    assert "boundary condition" in counterevidence.text
    assert "not reliable" in counterevidence.text
    assert all("sha256:" not in item.text for item in plan.multi_query.subqueries)


def test_single_study_with_coordinated_question_parts_remains_one_document() -> None:
    plan = plan_evidence_query(
        "Which specimens, tissues, and dates bounded the museum study, and what "
        "analysis remained possible?"
    )

    assert plan.document_breadth == 1
    assert plan.facet_subquery_ids == ()
