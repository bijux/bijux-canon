"""Semantic classification evidence for retrieved research candidates."""

from __future__ import annotations

import hashlib

from bijux_canon_reason.grounding import CitationEvidence, ImmutableEvidenceLocator
from bijux_canon_reason.grounding.provider_contracts import content_artifact_id
from bijux_canon_reason.research import (
    CandidateClassificationMethod,
    ResearchCandidateAdjudicationService,
    ResearchCandidateRelation,
    StructuredCandidateJudgment,
)


def _id(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode()).hexdigest()


def _evidence(value: str, text: str) -> CitationEvidence:
    return CitationEvidence(
        artifact_id=_id(value),
        chunk_artifact_id=_id(value + "-chunk"),
        retrieval_artifact_id=_id(value + "-retrieval"),
        document_id=value,
        source_id=value,
        section_path=("results",),
        locator=ImmutableEvidenceLocator(
            artifact_id=_id(value + "-locator"),
            source_artifact_id=_id(value + "-source"),
            source_uri=f"https://example.test/{value}",
            source_content_sha256=hashlib.sha256(value.encode()).hexdigest(),
            scheme="paragraph",
            selectors=(("paragraph_number", 1),),
        ),
        exact_text=text,
        exact_text_sha256=hashlib.sha256(text.encode()).hexdigest(),
        rank=1,
        relevance_score=1.0,
        claim_keys=(_id("question"),),
    )


def _judgment(
    evaluator: str,
    requirement: str,
    claim: str,
    evidence: str,
    relation: ResearchCandidateRelation,
) -> StructuredCandidateJudgment:
    payload = {
        "evaluator_id": evaluator,
        "requirement_artifact_id": requirement,
        "claim_artifact_id": claim,
        "evidence_artifact_id": evidence,
        "relation": relation.value,
        "confidence": 0.95,
        "entity_aligned": True,
        "scope_aligned": True,
        "qualifier_aligned": True,
        "negation_aligned": relation is not ResearchCandidateRelation.OPPOSING,
        "rationale": f"reviewed {relation.value}",
    }
    return StructuredCandidateJudgment.model_validate(
        {"artifact_id": content_artifact_id(payload), **payload}
    )


def test_real_petrous_content_is_classified_by_text_not_search_intent() -> None:
    statement = (
        "Dense petrous part C can yield up to 65-fold more endogenous DNA than part B."
    )
    support = _evidence("support", statement)
    unrelated = _evidence(
        "unrelated",
        "Corded Ware ancestry varies across independently defined European regions.",
    )
    report = ResearchCandidateAdjudicationService().classify(
        requirement_artifact_id=_id("requirement"),
        requirement_kind="opposition",
        target_statement=statement,
        claim_artifact_id=_id("claim"),
        candidates=(support, unrelated),
    )

    assert [item.relation for item in report.classifications] == [
        ResearchCandidateRelation.SUPPORTING,
        ResearchCandidateRelation.IRRELEVANT,
    ]
    assert report.classifications[0].locator_artifact_id == support.locator.artifact_id
    assert report.classifications[0].material
    assert not report.classifications[1].material


def test_negation_and_scope_traps_do_not_become_support() -> None:
    statement = "Petrous part C yielded more endogenous DNA than part B."
    negated = _evidence(
        "negated",
        "Petrous part C did not yield more endogenous DNA than part B.",
    )
    scope = _evidence(
        "scope",
        "Petrous part C yielded more endogenous DNA in one unreplicated regional sample.",
    )
    report = ResearchCandidateAdjudicationService().classify(
        requirement_artifact_id=_id("requirement"),
        requirement_kind="opposition",
        target_statement=statement,
        claim_artifact_id=_id("claim"),
        candidates=(negated, scope),
    )

    assert report.classifications[0].relation is ResearchCandidateRelation.OPPOSING
    assert report.classifications[1].relation is not ResearchCandidateRelation.SUPPORTING


def test_limitation_requires_related_limitation_content() -> None:
    evidence = _evidence(
        "limitation",
        "Petrous bone DNA preservation can fall below 1% in hot climates, limiting recovery.",
    )
    report = ResearchCandidateAdjudicationService().classify(
        requirement_artifact_id=_id("requirement"),
        requirement_kind="limitation",
        target_statement="Petrous bone DNA recovery in hot climates has limitations.",
        claim_artifact_id=None,
        candidates=(evidence,),
    )

    assert report.classifications[0].relation is ResearchCandidateRelation.LIMITING
    assert report.classifications[0].material


def test_duplicate_text_is_classified_once_with_exact_provenance() -> None:
    text = "Petrous part C yielded more endogenous DNA than part B."
    first = _evidence("first", text)
    duplicate = _evidence("duplicate", text)
    report = ResearchCandidateAdjudicationService().classify(
        requirement_artifact_id=_id("requirement"),
        requirement_kind="finding",
        target_statement=text,
        claim_artifact_id=_id("claim"),
        candidates=(first, duplicate),
    )

    assert len(report.classifications) == 1
    assert report.duplicates[0].evidence_artifact_id == duplicate.artifact_id
    assert report.duplicates[0].canonical_evidence_artifact_id == first.artifact_id


def test_adjudicator_disagreement_remains_material_and_unclassified() -> None:
    requirement = _id("requirement")
    claim = _id("claim")
    evidence = _evidence(
        "candidate", "Petrous part C yielded more endogenous DNA than part B."
    )
    judgments = (
        _judgment(
            "reviewer-a",
            requirement,
            claim,
            evidence.artifact_id,
            ResearchCandidateRelation.SUPPORTING,
        ),
        _judgment(
            "reviewer-b",
            requirement,
            claim,
            evidence.artifact_id,
            ResearchCandidateRelation.OPPOSING,
        ),
    )
    report = ResearchCandidateAdjudicationService().classify(
        requirement_artifact_id=requirement,
        requirement_kind="finding",
        target_statement=evidence.exact_text,
        claim_artifact_id=claim,
        candidates=(evidence,),
        judgments=judgments,
    )

    classification = report.classifications[0]
    assert classification.relation is ResearchCandidateRelation.UNCLASSIFIED
    assert classification.method is CandidateClassificationMethod.ADJUDICATOR_DISAGREEMENT
    assert classification.material
    assert report.material_unclassified_evidence_artifact_ids == (evidence.artifact_id,)
