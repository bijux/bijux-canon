# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Research graph evidence-relation attachment tests."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from bijux_canon_reason.grounding import (
    CitationIntegrityStatus,
    CitationVerificationOutcome,
    CitationVerificationReport,
    EntailmentVerdict,
    EvidenceEntailmentAssessment,
    VerifiedAtomicClaim,
)
from bijux_canon_reason.grounding.provider_contracts import content_artifact_id
from bijux_canon_reason.research import (
    EvidenceRelationAttachmentService,
    EvidenceRelationKind,
    RelationClassificationMode,
    RelationRejectionReason,
)

_REPO = Path(__file__).resolve().parents[5]


def _artifact(value: str) -> str:
    return "sha256:" + value * 64


def _assessment(
    *,
    claim: str,
    ordinal: int,
    evidence: str,
    verdict: EntailmentVerdict,
    coverage: float,
    exact: bool = False,
) -> EvidenceEntailmentAssessment:
    payload = {
        "claim_artifact_id": claim,
        "claim_ordinal": ordinal,
        "claim_citation_link_artifact_id": _artifact(evidence.lower()),
        "citation_evidence_artifact_id": _artifact(evidence),
        "integrity": CitationIntegrityStatus.verified.value,
        "verdict": verdict.value,
        "claim_term_coverage": coverage,
        "exact_claim_span": exact,
        "claim_negated": verdict is EntailmentVerdict.opposition,
        "evidence_negated": False,
        "rationale_code": f"verified_{verdict.value}",
    }
    return EvidenceEntailmentAssessment.model_validate(
        {"artifact_id": content_artifact_id(payload), **payload}
    )


def _verified_claim(
    claim_id: str,
    ordinal: int,
    verdict: EntailmentVerdict,
    assessments: tuple[EvidenceEntailmentAssessment, ...],
) -> VerifiedAtomicClaim:
    payload = {
        "claim_artifact_id": claim_id,
        "claim_ordinal": ordinal,
        "verdict": verdict.value,
        "assessments": tuple(item.model_dump(mode="json") for item in assessments),
    }
    return VerifiedAtomicClaim.model_validate(
        {"artifact_id": content_artifact_id(payload), **payload}
    )


def _report() -> CitationVerificationReport:
    first_id = _artifact("1")
    first_assessments = (
        _assessment(
            claim=first_id,
            ordinal=1,
            evidence="a",
            verdict=EntailmentVerdict.direct_support,
            coverage=1.0,
            exact=True,
        ),
        _assessment(
            claim=first_id,
            ordinal=1,
            evidence="b",
            verdict=EntailmentVerdict.opposition,
            coverage=0.9,
        ),
    )
    second_id = _artifact("2")
    second_assessments = (
        _assessment(
            claim=second_id,
            ordinal=2,
            evidence="c",
            verdict=EntailmentVerdict.ambiguity,
            coverage=0.7,
        ),
        _assessment(
            claim=second_id,
            ordinal=2,
            evidence="d",
            verdict=EntailmentVerdict.irrelevance,
            coverage=0.1,
        ),
        _assessment(
            claim=second_id,
            ordinal=2,
            evidence="e",
            verdict=EntailmentVerdict.insufficiency,
            coverage=0.2,
        ),
    )
    claims = (
        _verified_claim(first_id, 1, EntailmentVerdict.ambiguity, first_assessments),
        _verified_claim(second_id, 2, EntailmentVerdict.ambiguity, second_assessments),
    )
    payload = {
        "schema_version": "bijux.canon.reason.citation_verification_report.v1",
        "source_claim_set_artifact_id": _artifact("3"),
        "claim_citation_set_artifact_id": _artifact("4"),
        "policy_artifact_id": _artifact("5"),
        "outcome": CitationVerificationOutcome.claims_verified.value,
        "integrity_verified_links": 5,
        "integrity_total_links": 5,
        "claims": tuple(item.model_dump(mode="json") for item in claims),
    }
    return CitationVerificationReport.model_validate(
        {"artifact_id": content_artifact_id(payload), **payload}
    )


def test_support_opposition_and_ambiguity_remain_distinct_edges() -> None:
    attachment = EvidenceRelationAttachmentService().attach(
        graph_artifact_id=_artifact("6"),
        report=_report(),
        provider_provenance_artifact_id=_artifact("7"),
    )

    assert tuple(item.relation for item in attachment.relations) == (
        EvidenceRelationKind.supports,
        EvidenceRelationKind.opposes,
        EvidenceRelationKind.ambiguous,
    )
    assert attachment.relations[0].strength == 1.0
    assert attachment.relations[1].strength == 0.9
    assert len(attachment.traces) == 3
    assert all(
        item.classification_mode
        is RelationClassificationMode.deterministic_verification
        for item in attachment.traces
    )
    assert all(
        item.provider_provenance_artifact_id == _artifact("7")
        for item in attachment.traces
    )


def test_irrelevance_and_insufficiency_are_retained_without_false_edges() -> None:
    attachment = EvidenceRelationAttachmentService().attach(
        graph_artifact_id=_artifact("6"), report=_report()
    )

    assert tuple(item.reason for item in attachment.rejected) == (
        RelationRejectionReason.irrelevance,
        RelationRejectionReason.insufficiency,
    )
    assert not {
        item.assessment_artifact_id for item in attachment.rejected
    }.intersection(item.assessment_artifact_id for item in attachment.traces)


def test_admitted_relations_validate_against_public_v2_schema() -> None:
    attachment = EvidenceRelationAttachmentService().attach(
        graph_artifact_id=_artifact("6"), report=_report()
    )
    schema = json.loads(
        (
            _REPO / "apis/bijux-canon-reason/v2/reasoning-artifacts.schema.json"
        ).read_text()
    )
    validator = Draft202012Validator(schema)

    for relation in attachment.relations:
        validator.validate(relation.model_dump(mode="json"))


def test_no_claims_report_produces_an_empty_attachment() -> None:
    payload = {
        "schema_version": "bijux.canon.reason.citation_verification_report.v1",
        "source_claim_set_artifact_id": _artifact("3"),
        "claim_citation_set_artifact_id": _artifact("4"),
        "policy_artifact_id": _artifact("5"),
        "outcome": CitationVerificationOutcome.no_claims.value,
        "integrity_verified_links": 0,
        "integrity_total_links": 0,
        "claims": (),
    }
    report = CitationVerificationReport.model_validate(
        {"artifact_id": content_artifact_id(payload), **payload}
    )

    attachment = EvidenceRelationAttachmentService().attach(
        graph_artifact_id=_artifact("6"), report=report
    )

    assert attachment.relations == ()
    assert attachment.traces == ()
    assert attachment.rejected == ()
