# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import hashlib

import pytest

from bijux_canon_reason.grounding import (
    CitationEvidence,
    CitationSourceDescriptor,
    EvidencePacket,
    EvidencePacketBuilder,
    EvidencePacketPolicy,
    GroundingAdmissionOutcome,
    ImmutableEvidenceLocator,
    LocalGroundedAnswer,
    LocalGroundedAnswerService,
)
from bijux_canon_reason.grounding.provider_contracts import content_artifact_id
from bijux_canon_reason.research import (
    CandidateClassificationMethod,
    ClaimRevisionAction,
    ClaimRevisionActionKind,
    ResearchAnswerRevisionService,
    ResearchCandidateClassification,
    ResearchCandidateRelation,
    ResearchRevisionOutcome,
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _artifact(value: str) -> str:
    return f"sha256:{_sha(value)}"


def _evidence(name: str, text: str, rank: int = 1) -> CitationEvidence:
    return CitationEvidence(
        artifact_id=_artifact(f"evidence:{name}"),
        chunk_artifact_id=_artifact(f"chunk:{name}"),
        retrieval_artifact_id=_artifact(f"retrieval:{name}"),
        document_id=f"document-{name}",
        source_id=f"source-{name}",
        section_path=("article", "results"),
        locator=ImmutableEvidenceLocator(
            artifact_id=_artifact(f"locator:{name}"),
            source_artifact_id=_artifact(f"source:{name}"),
            source_uri=f"https://example.test/{name}",
            source_content_sha256=_sha(f"content:{name}"),
            scheme="unicode-code-point",
            selectors=(("char_start", 0), ("char_end", len(text))),
        ),
        exact_text=text,
        exact_text_sha256=_sha(text),
        rank=rank,
        relevance_score=1.0 / rank,
    )


def _source(name: str) -> CitationSourceDescriptor:
    return CitationSourceDescriptor.create(
        source_id=f"source-{name}",
        title=f"Study {name}",
        canonical_uri=f"https://example.test/{name}",
        doi=None,
        source_content_sha256=_sha(f"content:{name}"),
        authors=(f"Author {name}",),
        journal="Journal of Ancient DNA",
        publication_date="2026-08-24",
        license_expression="CC BY 4.0",
        license_url="https://creativecommons.org/licenses/by/4.0/",
        provenance_artifact_id=_artifact(f"provenance:{name}"),
    )


def _prior() -> tuple[LocalGroundedAnswer, EvidencePacket]:
    evidence = _evidence(
        "prior",
        "Petrous bone DNA recovery reached 65 percent in the tested samples.",
    )
    packet = EvidencePacketBuilder(
        EvidencePacketPolicy(
            token_budget=100,
            citation_budget=4,
            claim_budget=4,
            max_per_source=4,
            max_per_section=4,
        )
    ).build(
        question_artifact_id=_artifact("question"),
        scope_artifact_id=_artifact("scope"),
        retrieval_trace_artifact_ids=(evidence.retrieval_artifact_id,),
        candidates=(evidence,),
    )
    return (
        LocalGroundedAnswerService().answer(
            question="What petrous bone DNA recovery was reported?",
            evidence_packet=packet,
            sources=(_source("prior"),),
            max_points=4,
        ),
        packet,
    )


def _classification(
    evidence: CitationEvidence,
    claim_id: str,
    relation: ResearchCandidateRelation,
    *,
    material: bool = True,
) -> ResearchCandidateClassification:
    payload = {
        "schema_version": "bijux.canon.reason.candidate_classification.v1",
        "requirement_artifact_id": _artifact("requirement"),
        "claim_artifact_id": claim_id,
        "evidence_artifact_id": evidence.artifact_id,
        "locator_artifact_id": evidence.locator.artifact_id,
        "exact_text_sha256": evidence.exact_text_sha256,
        "relation": relation.value,
        "rationale": "reviewed exact evidence relation",
        "method": CandidateClassificationMethod.DETERMINISTIC_SEMANTIC.value,
        "confidence": 0.95,
        "material": material,
        "semantic_coverage": 0.95,
        "judgment_artifact_ids": (),
    }
    return ResearchCandidateClassification.model_validate(
        {"artifact_id": content_artifact_id(payload), **payload}
    )


def _revise(
    relation: ResearchCandidateRelation,
    text: str,
    *,
    material: bool = True,
):
    prior, packet = _prior()
    candidate = _evidence("candidate", text, 2)
    classification = _classification(
        candidate,
        prior.claims.claims[0].artifact_id,
        relation,
        material=material,
    )
    result = ResearchAnswerRevisionService().revise(
        prior_claim_graph_artifact_id=_artifact("claim-graph"),
        prior_answer=prior,
        prior_evidence_packet=packet,
        classifications=(classification,),
        candidate_evidence=(candidate,),
        sources=(_source("prior"), _source("candidate")),
    )
    return prior, candidate, classification, result


def test_supporting_evidence_strengthens_and_reverifies_the_answer() -> None:
    prior, candidate, classification, result = _revise(
        ResearchCandidateRelation.SUPPORTING,
        "A second study reported petrous bone DNA recovery of 65 percent.",
    )

    assert result.outcome is ResearchRevisionOutcome.REVISED
    assert result.before_answer == prior.answer_text
    assert result.after_answer != result.before_answer
    assert result.actions[0].kind is ClaimRevisionActionKind.STRENGTHEN
    assert result.actions[0].evidence_artifact_ids == (candidate.artifact_id,)
    assert result.resolved_classification_artifact_ids == (
        classification.artifact_id,
    )
    assert all(
        claim.verdict.value == "direct_support"
        for claim in result.revised_answer.verification.claims
    )
    assert result.revised_answer.admission.outcome in {
        GroundingAdmissionOutcome.admitted,
        GroundingAdmissionOutcome.partially_admitted,
    }


@pytest.mark.parametrize(
    ("relation", "text"),
    (
        (
            ResearchCandidateRelation.OPPOSING,
            "A second study did not find petrous bone DNA recovery of 65 percent.",
        ),
        (
            ResearchCandidateRelation.LIMITING,
            "A limitation was that petrous bone DNA recovery remained below 1 percent in hot climates.",
        ),
    ),
)
def test_opposition_and_limitations_visibly_qualify_the_answer(
    relation: ResearchCandidateRelation,
    text: str,
) -> None:
    prior, candidate, classification, result = _revise(relation, text)

    assert result.outcome is ResearchRevisionOutcome.REVISED
    assert result.after_answer != prior.answer_text
    assert result.actions[0].kind is ClaimRevisionActionKind.QUALIFY
    assert classification.artifact_id in result.actions[0].classification_artifact_ids
    assert candidate.exact_text in result.after_answer
    assert result.revised_answer.citations.links[-1].exact_text_sha256 == (
        candidate.exact_text_sha256
    )


def test_ambiguous_material_evidence_withdraws_the_prior_answer() -> None:
    prior, candidate, classification, result = _revise(
        ResearchCandidateRelation.AMBIGUOUS,
        "Petrous bone recovery may differ, but the reported percentage was unclear.",
    )

    assert result.outcome is ResearchRevisionOutcome.ABSTAINED
    assert result.revised_answer.outcome is GroundingAdmissionOutcome.abstained
    assert prior.claims.claims[0].statement not in result.after_answer
    assert result.actions[0].kind is ClaimRevisionActionKind.ABSTAIN
    assert result.unresolved_classification_artifact_ids == (
        classification.artifact_id,
    )
    assert result.actions[0].evidence_artifact_ids == (candidate.artifact_id,)


def test_irrelevant_nonmaterial_evidence_preserves_answer_with_lineage() -> None:
    prior, _candidate, classification, result = _revise(
        ResearchCandidateRelation.IRRELEVANT,
        "The laboratory building opened in 1994.",
        material=False,
    )

    assert result.outcome is ResearchRevisionOutcome.PRESERVED
    assert result.after_answer == prior.answer_text
    assert result.actions[0].kind is ClaimRevisionActionKind.PRESERVE
    assert result.resolved_classification_artifact_ids == (
        classification.artifact_id,
    )


def test_split_and_merge_actions_enforce_typed_lineage_shapes() -> None:
    claim_a = _artifact("claim-a")
    claim_b = _artifact("claim-b")
    claim_c = _artifact("claim-c")
    classification = _artifact("classification")
    evidence = _artifact("evidence")

    split = ClaimRevisionAction.create(
        kind=ClaimRevisionActionKind.SPLIT,
        prior_claim_artifact_ids=(claim_a,),
        revised_claim_artifact_ids=(claim_b, claim_c),
        evidence_artifact_ids=(evidence,),
        classification_artifact_ids=(classification,),
        rationale="one compound claim became two verified atomic claims",
    )
    merge = ClaimRevisionAction.create(
        kind=ClaimRevisionActionKind.MERGE,
        prior_claim_artifact_ids=(claim_b, claim_c),
        revised_claim_artifact_ids=(claim_a,),
        evidence_artifact_ids=(evidence,),
        classification_artifact_ids=(classification,),
        rationale="duplicate claims became one source-scoped verified claim",
    )

    assert split.kind is ClaimRevisionActionKind.SPLIT
    assert merge.kind is ClaimRevisionActionKind.MERGE
    with pytest.raises(ValueError, match="claim shape"):
        ClaimRevisionAction.create(
            kind=ClaimRevisionActionKind.SPLIT,
            prior_claim_artifact_ids=(claim_a, claim_b),
            revised_claim_artifact_ids=(claim_c,),
            evidence_artifact_ids=(evidence,),
            classification_artifact_ids=(classification,),
            rationale="invalid split",
        )
