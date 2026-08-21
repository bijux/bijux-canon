# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Research graph assumption and insufficiency tests."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from bijux_canon_reason.grounding import EvidenceGap, EvidenceGapCode
from bijux_canon_reason.grounding.provider_contracts import content_artifact_id
from bijux_canon_reason.research import (
    AssumptionImpact,
    AssumptionInsufficiencyService,
    ClaimSourceCoverage,
    EvidenceRelationAttachment,
    EvidenceRelationKind,
    EvidenceRelationTrace,
    GraphEvidenceRelation,
    InsufficiencyOutcome,
    RelationClassificationMode,
    ResearchDeficiencyKind,
    create_assumption_candidate,
)

_REPO = Path(__file__).resolve().parents[5]


def _artifact(value: str) -> str:
    return "sha256:" + value * 64


def _support_attachment(graph_id: str, claim_id: str) -> EvidenceRelationAttachment:
    relation_payload = {
        "schema_version": "2.0.0",
        "artifact_type": "bijux.canon.reason.evidence_relation",
        "claim_artifact_id": claim_id,
        "evidence_artifact_id": _artifact("3"),
        "relation": EvidenceRelationKind.supports.value,
        "strength": 1.0,
        "rationale": "verified_direct_support",
    }
    relation = GraphEvidenceRelation(
        artifact_id=content_artifact_id(relation_payload), **relation_payload
    )
    trace_payload = {
        "relation_artifact_id": relation.artifact_id,
        "assessment_artifact_id": _artifact("4"),
        "claim_citation_link_artifact_id": _artifact("5"),
        "citation_evidence_artifact_id": relation.evidence_artifact_id,
        "integrity": "verified",
        "deterministic_policy_artifact_id": _artifact("6"),
        "verification_report_artifact_id": _artifact("7"),
        "provider_provenance_artifact_id": None,
        "classification_mode": RelationClassificationMode.deterministic_verification.value,
    }
    trace = EvidenceRelationTrace(
        artifact_id=content_artifact_id(trace_payload), **trace_payload
    )
    attachment_payload = {
        "schema_version": "bijux.canon.reason.evidence_relation_attachment.v1",
        "graph_artifact_id": graph_id,
        "verification_report_artifact_id": _artifact("7"),
        "relations": (relation.model_dump(mode="json"),),
        "traces": (trace.model_dump(mode="json"),),
        "rejected": (),
    }
    return EvidenceRelationAttachment(
        artifact_id=content_artifact_id(attachment_payload),
        graph_artifact_id=graph_id,
        verification_report_artifact_id=_artifact("7"),
        relations=(relation,),
        traces=(trace,),
        rejected=(),
    )


def _gap(code: EvidenceGapCode, claim_id: str | None, suffix: str) -> EvidenceGap:
    payload = {
        "code": code.value,
        "claim_artifact_id": claim_id,
        "detail": f"Observed {code.value} condition {suffix}.",
        "required_action": f"Resolve {code.value} condition {suffix}.",
    }
    return EvidenceGap(artifact_id=content_artifact_id(payload), **payload)


def test_materializes_every_required_deficiency_and_support_boundary() -> None:
    graph_id = _artifact("8")
    supported_claim = _artifact("1")
    unsupported_claim = _artifact("2")
    attachment = _support_attachment(graph_id, supported_claim)
    assumption = create_assumption_candidate(
        claim_artifact_id=supported_claim,
        statement="  The measured cohort represents the target population. ",
        impact=AssumptionImpact.high,
        provenance_artifact_id=_artifact("9"),
    )

    result = AssumptionInsufficiencyService().assess(
        graph_artifact_id=graph_id,
        claim_artifact_ids=(supported_claim, unsupported_claim),
        relation_attachment=attachment,
        minimum_supports=1,
        minimum_independent_sources=2,
        assumptions=(assumption,),
        evidence_gaps=(
            _gap(EvidenceGapCode.no_retrieved_evidence, unsupported_claim, "a"),
            _gap(EvidenceGapCode.out_of_scope, None, "b"),
            _gap(EvidenceGapCode.fabricated_entity, None, "c"),
        ),
        source_coverage=(
            ClaimSourceCoverage(
                claim_artifact_id=supported_claim,
                source_artifact_ids=(_artifact("a"),),
            ),
        ),
    )

    assert result.assumptions[0].statement == (
        "The measured cohort represents the target population."
    )
    assert tuple(item.outcome for item in result.insufficiencies) == (
        InsufficiencyOutcome.sufficient,
        InsufficiencyOutcome.insufficient,
    )
    assert result.insufficiencies[1].missing_information == (
        "1 additional direct support relation(s)",
    )
    assert {item.kind for item in result.deficiencies} == set(ResearchDeficiencyKind)
    assert (
        AssumptionInsufficiencyService().assess(
            graph_artifact_id=graph_id,
            claim_artifact_ids=(supported_claim, unsupported_claim),
            relation_attachment=attachment,
            minimum_supports=1,
            minimum_independent_sources=2,
            assumptions=(assumption,),
            evidence_gaps=(
                _gap(EvidenceGapCode.no_retrieved_evidence, unsupported_claim, "a"),
                _gap(EvidenceGapCode.out_of_scope, None, "b"),
                _gap(EvidenceGapCode.fabricated_entity, None, "c"),
            ),
            source_coverage=(
                ClaimSourceCoverage(
                    claim_artifact_id=supported_claim,
                    source_artifact_ids=(_artifact("a"),),
                ),
            ),
        )
        == result
    )


def test_public_assumption_and_insufficiency_nodes_validate_as_v2() -> None:
    graph_id = _artifact("8")
    claim_id = _artifact("1")
    attachment = _support_attachment(graph_id, claim_id)
    result = AssumptionInsufficiencyService().assess(
        graph_artifact_id=graph_id,
        claim_artifact_ids=(claim_id,),
        relation_attachment=attachment,
        minimum_supports=1,
        assumptions=(
            create_assumption_candidate(
                claim_artifact_id=claim_id,
                statement="The source population is applicable.",
                impact=AssumptionImpact.medium,
            ),
        ),
    )
    schema = json.loads(
        (
            _REPO / "apis/bijux-canon-reason/v2/reasoning-artifacts.schema.json"
        ).read_text()
    )
    validator = Draft202012Validator(schema)

    validator.validate(result.assumptions[0].model_dump(mode="json"))
    validator.validate(result.insufficiencies[0].model_dump(mode="json"))


@pytest.mark.parametrize("field", ["claim", "gap", "coverage", "relation"])
def test_rejects_unknown_claim_references(field: str) -> None:
    graph_id = _artifact("8")
    claim_id = _artifact("1")
    unknown = _artifact("2")
    kwargs: dict[str, object] = {}
    if field == "claim":
        kwargs["assumptions"] = (
            create_assumption_candidate(
                claim_artifact_id=unknown,
                statement="An unknown premise.",
                impact=AssumptionImpact.low,
            ),
        )
    elif field == "gap":
        kwargs["evidence_gaps"] = (
            _gap(EvidenceGapCode.insufficient_evidence, unknown, "x"),
        )
    elif field == "coverage":
        kwargs["source_coverage"] = (
            ClaimSourceCoverage(
                claim_artifact_id=unknown,
                source_artifact_ids=(_artifact("a"),),
            ),
        )

    attachment = _support_attachment(
        graph_id, unknown if field == "relation" else claim_id
    )
    with pytest.raises(ValueError, match="unknown claim"):
        AssumptionInsufficiencyService().assess(
            graph_artifact_id=graph_id,
            claim_artifact_ids=(claim_id,),
            relation_attachment=attachment,
            minimum_supports=1,
            **kwargs,
        )


@pytest.mark.parametrize(
    ("minimum_supports", "minimum_independent_sources"), ((0, 2), (1, 0))
)
def test_rejects_nonpositive_policy_thresholds(
    minimum_supports: int, minimum_independent_sources: int
) -> None:
    graph_id = _artifact("8")
    claim_id = _artifact("1")

    with pytest.raises(ValueError, match="thresholds must be positive"):
        AssumptionInsufficiencyService().assess(
            graph_artifact_id=graph_id,
            claim_artifact_ids=(claim_id,),
            relation_attachment=_support_attachment(graph_id, claim_id),
            minimum_supports=minimum_supports,
            minimum_independent_sources=minimum_independent_sources,
        )
