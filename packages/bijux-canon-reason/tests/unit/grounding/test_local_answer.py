# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import hashlib

from bijux_canon_reason.grounding import (
    CitationEvidence,
    CitationSourceDescriptor,
    EvidencePacketBuilder,
    EvidencePacketPolicy,
    GroundingAdmissionOutcome,
    ImmutableEvidenceLocator,
    LocalGroundedAnswer,
    LocalGroundedAnswerService,
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _artifact(value: str) -> str:
    return f"sha256:{_sha(value)}"


def _evidence(name: str, text: str, rank: int) -> CitationEvidence:
    return CitationEvidence(
        artifact_id=_artifact(f"evidence:{name}"),
        chunk_artifact_id=_artifact(f"chunk:{name}"),
        retrieval_artifact_id=_artifact("retrieval"),
        document_id=f"document-{name}",
        source_id=f"source-{name}",
        section_path=("article", "results"),
        locator=ImmutableEvidenceLocator(
            artifact_id=_artifact(f"locator:{name}"),
            source_artifact_id=_artifact(f"source:{name}"),
            source_uri=f"https://example.test/{name}",
            source_content_sha256=_sha(f"source-content:{name}"),
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
        title=f"Source {name}",
        canonical_uri=f"https://example.test/{name}",
        doi=None,
        source_content_sha256=_sha(f"source-content:{name}"),
    )


def _answer(question: str, *evidence: CitationEvidence) -> LocalGroundedAnswer:
    packet = EvidencePacketBuilder(
        EvidencePacketPolicy(
            token_budget=500,
            citation_budget=8,
            claim_budget=8,
            max_per_source=4,
            max_per_section=8,
        )
    ).build(
        question_artifact_id=_artifact("question"),
        scope_artifact_id=_artifact("scope"),
        retrieval_trace_artifact_ids=(_artifact("trace"),),
        candidates=evidence,
    )
    source_names = tuple(item.source_id.removeprefix("source-") for item in evidence)
    return LocalGroundedAnswerService().answer(
        question=question,
        evidence_packet=packet,
        sources=tuple(_source(name) for name in source_names),
        max_points=8,
    )


def test_local_answer_admits_exact_claims_with_complete_context() -> None:
    result = _answer(
        "What DNA yield was reported?",
        _evidence("alpha", "Endogenous DNA yield reached 65 percent.", 1),
    )
    restarted = LocalGroundedAnswer.model_validate_json(result.model_dump_json())

    assert restarted == result
    assert result.outcome is GroundingAdmissionOutcome.admitted
    assert result.answer_text.startswith("Answer:\n-")
    assert result.claims.claims[0].statement == (
        "Endogenous DNA yield reached 65 percent."
    )
    assert result.verification.claims[0].verdict.value == "direct_support"
    assert result.contextualized.contexts[0].source_quality.value == "unknown"
    assert result.citations.links[0].exact_text_sha256 == _sha(
        "Endogenous DNA yield reached 65 percent."
    )


def test_local_answer_abstains_without_claim_leakage_for_unsupported_guarantee() -> (
    None
):
    result = _answer(
        "Does this method guarantee perfect DNA recovery?",
        _evidence(
            "bounded",
            "DNA recovery varied among samples and preservation contexts.",
            1,
        ),
    )

    assert result.outcome is GroundingAdmissionOutcome.abstained
    assert result.claims.claims == ()
    assert "DNA recovery varied" not in result.answer_text
    assert result.answer_text.startswith("Insufficient evidence.")
    assert result.admission.evidence_gaps


def test_conflict_question_preserves_divergence_without_claiming_contradiction() -> (
    None
):
    result = _answer(
        "What conflict or counterevidence did the two sources report?",
        _evidence("alpha", "The first assay detected ancient DNA.", 1),
        _evidence("beta", "The second assay did not detect ancient DNA.", 2),
    )

    assert result.outcome is GroundingAdmissionOutcome.admitted
    assert len(result.contextualized.conflicts) == 1
    conflict = result.contextualized.conflicts[0]
    assert conflict.relationship.value == "divergent"
    assert "contradiction is not asserted" in conflict.scope_note
