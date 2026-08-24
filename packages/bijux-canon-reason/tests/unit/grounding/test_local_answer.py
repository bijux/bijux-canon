# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

import pytest

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
        authors=(f"Author {name}",),
        journal="Journal of Exact Evidence",
        publication_date="2026-08-24",
        license_expression="CC BY 4.0",
        license_url="https://creativecommons.org/licenses/by/4.0/",
        provenance_artifact_id=_artifact(f"metadata:{name}"),
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
    assert result.answer_text.startswith("Source-supported findings:\n")
    assert result.claims.claims[0].statement == (
        "Endogenous DNA yield reached 65 percent."
    )
    assert result.verification.claims[0].verdict.value == "direct_support"
    assert result.contextualized.contexts[0].source_quality.value == "unknown"
    assert result.citations.links[0].exact_text_sha256 == _sha(
        "Endogenous DNA yield reached 65 percent."
    )
    assert "[citation:" not in result.answer_text
    assert "Citations:\n[1] Author alpha. Source alpha." in result.answer_text
    assert "Journal of Exact Evidence" in result.answer_text
    assert "Exact quote (sha256:" in result.answer_text
    assert "Locator: unicode-code-point(char_start=0" in result.answer_text
    assert f"Metadata provenance: {_artifact('metadata:alpha')}" in result.answer_text


def test_local_answer_admits_a_reproducible_concise_projection() -> None:
    source_text = "Our results show that endogenous DNA yields can remain below 1%."
    result = _answer(
        "What endogenous DNA yield limitation was reported?",
        _evidence("projection", source_text, 1),
    )

    assert result.outcome is GroundingAdmissionOutcome.admitted
    answer_body, citation_display = result.answer_text.split("\nCitations:\n", 1)
    assert "Our results show that" not in answer_body
    assert "Our results show that" in citation_display
    assert result.claims.claims[0].statement == (
        "Endogenous DNA yields can remain below 1%."
    )
    assert result.citations.links[0].exact_text == source_text
    assessment = result.verification.claims[0].assessments[0]
    assert assessment.verdict.value == "direct_support"
    assert assessment.rationale_code == "claim_is_verified_conservative_projection"


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
    assert len(result.citation_presentation.entries) == 2
    assert {entry.source_id for entry in result.citation_presentation.entries} == {
        "source-alpha",
        "source-beta",
    }
    conflict = result.contextualized.conflicts[0]
    assert conflict.relationship.value == "divergent"
    assert "scientific equivalence is not assumed" in conflict.scope_note
    assert "Unresolved conflicts and ambiguity:" in result.answer_text
    assert "[1, 2]" in result.answer_text


def test_reported_limitation_is_a_cited_record_not_an_uncited_footnote() -> None:
    result = _answer(
        "What limitation did the study report?",
        _evidence(
            "limited",
            "A limitation was that DNA recovery varied among sampled tissues.",
            1,
        ),
    )

    assert result.outcome is GroundingAdmissionOutcome.admitted
    assert result.contextualized.contexts[0].presentation_role.value == "limitation"
    assert "Cited limitations:" in result.answer_text
    assert "DNA recovery varied among sampled tissues" in result.answer_text
    assert "[1]" in result.answer_text
    assert "Answer limitations (not source-supported facts):" in result.answer_text


def test_petrous_content_answer_separates_finding_from_cited_limitation() -> None:
    result = _answer(
        (
            "Which petrous-bone region produced the highest endogenous DNA yield, "
            "by how much, and what hot-climate limitation was reported?"
        ),
        _evidence(
            "pinhasi-finding",
            (
                "Dense petrous part C exceeded part B by up to 65-fold and part A "
                "by up to 177-fold."
            ),
            1,
        ),
        _evidence(
            "pinhasi-limit",
            (
                "A limitation was that petrous-bone DNA preservation could fall "
                "below 1 percent in hot climates."
            ),
            2,
        ),
    )

    assert result.outcome is GroundingAdmissionOutcome.admitted
    assert "Source-supported findings:" in result.answer_text
    assert "Cited limitations:" in result.answer_text
    assert "65-fold" in result.answer_text
    assert "177-fold" in result.answer_text
    assert "below 1 percent" in result.answer_text
    assert {context.presentation_role.value for context in result.contextualized.contexts} == {
        "finding",
        "limitation",
    }
    assert len(result.citation_presentation.entries) == 2
    assert all(link.exact_text in result.answer_text for link in result.citations.links)


@pytest.mark.parametrize(
    "format_id",
    ("jats", "pdf-digital", "html", "docx", "markdown", "text"),
)
def test_real_supported_format_citations_round_trip_to_reviewed_source_truth(
    format_id: str,
) -> None:
    repository = Path(__file__).resolve().parents[5]
    portfolio = repository / "examples" / "document-formats"
    truth = next(
        json.loads(line)
        for line in (portfolio / "locator-truth.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
        if json.loads(line)["format_id"] == format_id
        and json.loads(line)["disposition"] == "verified_admitted"
    )
    sources = {
        item["parser_source_id"]: item
        for item in (
            json.loads(line)
            for line in (portfolio / "sources.jsonl").read_text(
                encoding="utf-8"
            ).splitlines()
        )
    }
    source_record = sources[truth["parser_source_id"]]
    source_path = portfolio / truth["media_path"]
    assert hashlib.sha256(source_path.read_bytes()).hexdigest() == truth["source_sha256"]
    selectors = tuple(truth["locator"].items())
    exact_text = truth["exact_text"]
    evidence = CitationEvidence(
        artifact_id=_artifact(f"evidence:{truth['truth_id']}"),
        chunk_artifact_id=_artifact(f"chunk:{truth['truth_id']}"),
        retrieval_artifact_id=_artifact(f"retrieval:{format_id}"),
        document_id=_artifact(f"document:{truth['parser_source_id']}"),
        source_id=truth["parser_source_id"],
        section_path=(format_id, truth["block_role"]),
        locator=ImmutableEvidenceLocator(
            artifact_id=_artifact(f"locator:{truth['truth_identity_sha256']}"),
            source_artifact_id=f"sha256:{truth['source_sha256']}",
            source_uri=source_record["canonical_uri"],
            source_content_sha256=truth["source_sha256"],
            scheme=truth["locator_scheme"],
            selectors=selectors,
        ),
        exact_text=exact_text,
        exact_text_sha256=truth["exact_text_sha256"],
        rank=1,
        relevance_score=1.0,
    )
    packet = EvidencePacketBuilder(
        EvidencePacketPolicy(
            token_budget=4096,
            citation_budget=1,
            claim_budget=1,
            max_per_source=1,
            max_per_section=1,
        )
    ).build(
        question_artifact_id=_artifact(f"question:{format_id}"),
        scope_artifact_id=_artifact("all-supported-formats"),
        retrieval_trace_artifact_ids=(evidence.retrieval_artifact_id,),
        candidates=(evidence,),
    )
    license_record = source_record["license"]
    source = CitationSourceDescriptor.create(
        source_id=evidence.source_id,
        title=source_record["title"],
        canonical_uri=source_record["canonical_uri"],
        doi=(
            source_record["canonical_uri"].removeprefix("https://doi.org/")
            if source_record["canonical_uri"].startswith("https://doi.org/")
            else None
        ),
        source_content_sha256=truth["source_sha256"],
        authors=tuple(source_record["authors"]),
        publication_date=source_record["publication_date"],
        license_expression=license_record["expression"],
        license_url=license_record["url"],
        provenance_artifact_id=f"sha256:{truth['truth_identity_sha256']}",
        format_id=format_id,
    )

    question_term = re.findall(r"[^\W_]+", exact_text, flags=re.UNICODE)[0]
    result = LocalGroundedAnswerService().answer(
        question=f"What does the source report about {question_term}?",
        evidence_packet=packet,
        sources=(source,),
        max_points=1,
    )

    assert result.outcome is GroundingAdmissionOutcome.admitted
    entry = result.citation_presentation.entries[0]
    assert entry.exact_quote == exact_text
    assert entry.exact_quote_sha256 == truth["exact_text_sha256"]
    assert entry.source_content_sha256 == truth["source_sha256"]
    assert entry.locator_scheme == truth["locator_scheme"]
    assert entry.locator_selectors == selectors
    assert entry.format_id == format_id
    assert f"Locator: {truth['locator_scheme']}(" in result.answer_text
