# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Atomic claim normalization, span, and failure tests."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json

from pydantic import ValidationError
import pytest

from bijux_canon_reason.grounding import (
    AtomicClaim,
    AtomicClaimNormalizer,
    AtomicClaimPolarity,
    CitationEvidence,
    ClaimConfidenceBasis,
    ClaimContentKind,
    ClaimModality,
    ClaimNormalizationError,
    ClaimNormalizationErrorCode,
    ClaimNormalizationOutcome,
    CredentialFreeSynthesizer,
    EvidencePacket,
    EvidencePacketBuilder,
    EvidencePacketPolicy,
    ImmutableEvidenceLocator,
    JsonHttpResponse,
    NormalizedClaimSet,
    OpenAICompatibleStructuredSynthesizer,
    StructuredProviderConfiguration,
    StructuredProviderError,
    StructuredProviderErrorCode,
    StructuredProviderSynthesis,
)
from bijux_canon_reason.grounding.provider_contracts import content_artifact_id


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _artifact(value: str) -> str:
    return f"sha256:{_sha(value)}"


def _packet(*, empty: bool = False) -> tuple[EvidencePacket, CitationEvidence]:
    text = "Ancient DNA fragments were shorter; the control remained unchanged."
    evidence = CitationEvidence(
        artifact_id=_artifact("evidence"),
        chunk_artifact_id=_artifact("chunk"),
        retrieval_artifact_id=_artifact("retrieval"),
        document_id="document",
        source_id="source",
        section_path=("results",),
        locator=ImmutableEvidenceLocator(
            artifact_id=_artifact("locator"),
            source_artifact_id=_artifact("source"),
            source_uri="https://example.test/source",
            source_content_sha256=_sha("source-content"),
            scheme="unicode-code-point",
            selectors=(("char_start", 0), ("char_end", len(text))),
        ),
        exact_text=text,
        exact_text_sha256=_sha(text),
        rank=1,
        relevance_score=1.0,
        claim_keys=("claim",),
    )
    packet = EvidencePacketBuilder(
        EvidencePacketPolicy(
            token_budget=100,
            citation_budget=1,
            claim_budget=1,
            max_per_source=1,
            max_per_section=1,
        )
    ).build(
        question_artifact_id=_artifact("question"),
        scope_artifact_id=_artifact("scope"),
        retrieval_trace_artifact_ids=(_artifact("trace"),),
        candidates=() if empty else (evidence,),
    )
    return packet, evidence


class _Transport:
    def __init__(self, candidate: Mapping[str, object]) -> None:
        self.candidate = candidate

    def post_json(
        self,
        url: str,
        *,
        headers: dict[str, str],
        body: bytes,
        timeout_seconds: float,
        max_response_bytes: int,
    ) -> JsonHttpResponse:
        del url, headers, body, timeout_seconds, max_response_bytes
        envelope = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": json.dumps(self.candidate),
                    }
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 10},
        }
        return JsonHttpResponse(200, json.dumps(envelope).encode(), 1, "request")


def _provider_result(
    statement: str | tuple[str, ...], answer: str
) -> tuple[StructuredProviderSynthesis, CitationEvidence]:
    packet, evidence = _packet()
    statements = (statement,) if isinstance(statement, str) else statement
    candidate = {
        "schema_version": "bijux.canon.reason.provider_synthesis_candidate.v1",
        "outcome": "answered",
        "answer": answer,
        "claims": [
            {
                "statement": item,
                "citation_evidence_artifact_ids": [evidence.artifact_id],
                "polarity": "opposes",
                "qualifier": "within the tested samples",
                "scope": "the source study",
            }
            for item in statements
        ],
        "limitations": ["Source-scoped candidate."],
        "conflicts": [],
        "assumptions": [],
    }
    provider = OpenAICompatibleStructuredSynthesizer(
        StructuredProviderConfiguration(
            base_url="http://127.0.0.1:8000",
            model="test-model",
        ),
        credential_resolver=lambda: "secret",
        transport=_Transport(candidate),
    )
    return provider.synthesize(question="Question?", evidence_packet=packet), evidence


def test_compound_provider_claim_splits_without_collapsing_assertions() -> None:
    statement = (
        "The method increased yield; the control remained unchanged "
        "and the study reported no contamination."
    )
    provider_result, evidence = _provider_result(statement, statement)

    result = AtomicClaimNormalizer().normalize_provider(provider_result)

    assert tuple(claim.statement for claim in result.claims) == (
        "The method increased yield",
        "the control remained unchanged",
        "the study reported no contamination.",
    )
    assert all(claim.scope == "the source study" for claim in result.claims)
    assert all(
        claim.qualification.source_qualifier == "within the tested samples"
        for claim in result.claims
    )
    assert all(claim.polarity is AtomicClaimPolarity.opposes for claim in result.claims)
    assert all(
        claim.confidence_basis is ClaimConfidenceBasis.structured_provider_candidate
        for claim in result.claims
    )
    assert all(
        claim.citation_evidence_artifact_ids == (evidence.artifact_id,)
        for claim in result.claims
    )
    assert all(
        provider_result.candidate.answer[claim.answer_span[0] : claim.answer_span[1]]
        == claim.statement
        for claim in result.claims
    )


def test_atomic_claim_retains_negation_modality_population_time_and_quantity() -> None:
    statement = "At least one of the snakes may not retain useful DNA after 120 years."
    provider_result, _ = _provider_result(statement, statement)

    claim = AtomicClaimNormalizer().normalize_provider(provider_result).claims[0]

    assert claim.qualification.content_kind is ClaimContentKind.factual_assertion
    assert claim.qualification.modality is ClaimModality.possible
    assert claim.qualification.negated is True
    assert claim.qualification.population_scope == ("At least one of the snakes",)
    assert claim.qualification.temporal_scope == ("120 years",)
    assert claim.qualification.quantitative_scope == ("120",)
    assert claim.answer_quote == statement


def test_recommendation_is_typed_without_erasing_its_modality() -> None:
    statement = "Future studies should test additional hot-region samples."
    provider_result, _ = _provider_result(statement, statement)

    claim = AtomicClaimNormalizer().normalize_provider(provider_result).claims[0]

    assert claim.qualification.content_kind is ClaimContentKind.recommendation
    assert claim.qualification.modality is ClaimModality.recommended


@pytest.mark.parametrize(
    "statement",
    (
        "In my opinion, this method is elegant.",
        "However.",
    ),
)
def test_non_factual_candidate_cannot_enter_claim_metrics(statement: str) -> None:
    provider_result, _ = _provider_result(statement, statement)

    with pytest.raises(ClaimNormalizationError) as caught:
        AtomicClaimNormalizer().normalize_provider(provider_result)

    assert caught.value.code is ClaimNormalizationErrorCode.candidate_not_factual
    assert caught.value.content_kind in {
        ClaimContentKind.opinion,
        ClaimContentKind.transition,
    }


def test_noun_phrase_conjunction_is_not_split() -> None:
    statement = "DNA and RNA fragments degraded."
    provider_result, _ = _provider_result(statement, statement)

    result = AtomicClaimNormalizer().normalize_provider(provider_result)

    assert len(result.claims) == 1
    assert result.claims[0].statement == statement


def test_dependent_comparison_conjunction_is_not_split_into_an_orphan() -> None:
    statement = "Part C exceeded part B by 65-fold and those from part A by 177-fold."
    provider_result, _ = _provider_result(statement, statement)

    result = AtomicClaimNormalizer().normalize_provider(provider_result)

    assert tuple(claim.statement for claim in result.claims) == (statement,)


def test_definition_list_is_not_split_into_a_noun_phrase() -> None:
    statement = (
        "The sampled areas were cortical bone (part A), the otic capsule edge "
        "(part B), and the dense part within the otic capsule (part C)."
    )
    provider_result, _ = _provider_result(statement, statement)

    result = AtomicClaimNormalizer().normalize_provider(provider_result)

    assert tuple(claim.statement for claim in result.claims) == (statement,)


def test_leading_concession_splits_finding_from_limitation_with_exact_spans() -> None:
    statement = (
        "While endogenous yields were below 1% for samples from hot regions, "
        "damage patterns indicated ancient molecules."
    )
    provider_result, _ = _provider_result(statement, statement)

    result = AtomicClaimNormalizer().normalize_provider(provider_result)

    assert tuple(claim.statement for claim in result.claims) == (
        "endogenous yields were below 1% for samples from hot regions",
        "damage patterns indicated ancient molecules.",
    )
    first = result.claims[0]
    assert first.qualification.population_scope == ("samples from hot regions",)
    assert first.qualification.quantitative_scope == ("below 1%",)
    assert all(
        statement[claim.answer_span[0] : claim.answer_span[1]] == claim.statement
        for claim in result.claims
    )


def test_inline_concession_splits_capability_from_uncertain_boundary() -> None:
    statement = (
        "Genomic study of resin-embedded organisms is possible, although the "
        "time limits remain to be determined."
    )
    provider_result, _ = _provider_result(statement, statement)

    result = AtomicClaimNormalizer().normalize_provider(provider_result)

    assert tuple(claim.qualification.modality for claim in result.claims) == (
        ClaimModality.possible,
        ClaimModality.uncertain,
    )
    assert tuple(claim.statement for claim in result.claims) == (
        "Genomic study of resin-embedded organisms is possible",
        "the time limits remain to be determined.",
    )


def test_claim_ordinals_follow_answer_spans_not_provider_candidate_order() -> None:
    first = "The earlier result was observed."
    second = "The later result remained stable."
    answer = f"{first} {second}"
    provider_result, _ = _provider_result((second, first), answer)

    result = AtomicClaimNormalizer().normalize_provider(provider_result)

    assert tuple(claim.statement for claim in result.claims) == (first, second)
    assert tuple(claim.ordinal for claim in result.claims) == (1, 2)
    assert tuple(claim.source_candidate_ordinal for claim in result.claims) == (2, 1)
    assert result.claims[0].answer_span[1] < result.claims[1].answer_span[0]


def test_credential_free_points_keep_exact_answer_and_citation_spans() -> None:
    packet, evidence = _packet()
    synthesis = CredentialFreeSynthesizer().synthesize(
        question="What changed?", evidence_packet=packet
    )

    result = AtomicClaimNormalizer().normalize_credential_free(synthesis)

    assert result.outcome is ClaimNormalizationOutcome.claims_extracted
    assert len(result.claims) == 1
    assert all(claim.scope == "source" for claim in result.claims)
    assert all(
        claim.polarity is AtomicClaimPolarity.observed for claim in result.claims
    )
    assert all(
        synthesis.answer_text[claim.answer_span[0] : claim.answer_span[1]]
        == claim.statement
        for claim in result.claims
    )
    assert all(
        claim.citation_evidence_artifact_ids == (evidence.artifact_id,)
        for claim in result.claims
    )
    assert all(
        claim.confidence_basis is ClaimConfidenceBasis.conservative_evidence_projection
        for claim in result.claims
    )
    assert all(
        claim.atomicity_basis.startswith("conservative-projection:")
        for claim in result.claims
    )


def test_missing_provider_answer_span_fails_at_provider_boundary() -> None:
    with pytest.raises(StructuredProviderError) as caught:
        _provider_result("A candidate claim.", "An answer that omits the candidate.")

    assert caught.value.code is StructuredProviderErrorCode.attempts_exhausted
    assert all(
        attempt.validation_error_codes == ("answer_contains_unlinked_text",)
        for attempt in caught.value.attempts
    )


def test_repeated_provider_answer_span_fails_at_provider_boundary() -> None:
    with pytest.raises(StructuredProviderError) as caught:
        _provider_result("A repeated claim.", "A repeated claim. A repeated claim.")

    assert caught.value.code is StructuredProviderErrorCode.attempts_exhausted
    assert all(
        attempt.validation_error_codes == ("answer_contains_unlinked_text",)
        for attempt in caught.value.attempts
    )


def test_question_is_not_admitted_as_a_falsifiable_claim() -> None:
    provider_result, _ = _provider_result("What happened?", "What happened?")

    with pytest.raises(ClaimNormalizationError) as caught:
        AtomicClaimNormalizer().normalize_provider(provider_result)

    assert caught.value.code is ClaimNormalizationErrorCode.candidate_not_falsifiable


def test_coordinated_participle_stays_with_its_governing_claim() -> None:
    statement = (
        "The oldest RNA to have been sequenced and verified is over 700 years old."
    )
    provider_result, _ = _provider_result(statement, statement)

    result = AtomicClaimNormalizer().normalize_provider(provider_result)

    assert tuple(claim.statement for claim in result.claims) == (statement,)


def test_insufficient_offline_synthesis_has_honest_empty_claim_set() -> None:
    packet, _ = _packet(empty=True)
    synthesis = CredentialFreeSynthesizer().synthesize(
        question="Unknown?", evidence_packet=packet
    )

    result = AtomicClaimNormalizer().normalize_credential_free(synthesis)

    assert result.outcome is ClaimNormalizationOutcome.no_claims
    assert result.claims == ()


def test_normalized_claim_set_is_deterministic_and_restart_safe() -> None:
    provider_result, _ = _provider_result(
        "A stable claim remained.", "A stable claim remained."
    )
    normalizer = AtomicClaimNormalizer()

    first = normalizer.normalize_provider(provider_result)
    second = normalizer.normalize_provider(provider_result)
    restarted = NormalizedClaimSet.model_validate_json(first.model_dump_json())

    assert first == second == restarted


def test_historical_plain_qualifier_claim_replays_without_identity_change() -> None:
    statement = "A historical claim remained stable."
    claim_payload = {
        "ordinal": 1,
        "statement": statement,
        "statement_sha256": _sha(statement),
        "answer_span": (0, len(statement)),
        "answer_quote": statement,
        "answer_quote_sha256": _sha(statement),
        "qualifier": "within the historical source",
        "scope": "historical-source",
        "polarity": "observed",
        "confidence_basis": "exact_extractive_span",
        "citation_evidence_artifact_ids": (_artifact("historical-evidence"),),
        "source_candidate_ordinal": 1,
        "atomicity_basis": "single_assertion",
    }
    claim = AtomicClaim.model_validate(
        {"artifact_id": content_artifact_id(claim_payload), **claim_payload}
    )
    claim_set_payload = {
        "schema_version": "bijux.canon.reason.normalized_claim_set.v1",
        "source_synthesis_artifact_id": _artifact("historical-synthesis"),
        "answer_text_sha256": _sha(statement),
        "outcome": "claims_extracted",
        "claims": (claim.model_dump(mode="json"),),
    }

    replayed = NormalizedClaimSet.model_validate(
        {"artifact_id": content_artifact_id(claim_set_payload), **claim_set_payload}
    )

    assert replayed.claims[0].qualifier == "within the historical source"
    assert (
        replayed.claims[0].qualification.source_qualifier
        == "within the historical source"
    )
    assert replayed.artifact_id == content_artifact_id(claim_set_payload)


def test_normalized_claim_set_rejects_identity_drift() -> None:
    provider_result, _ = _provider_result(
        "A stable claim remained.", "A stable claim remained."
    )
    result = AtomicClaimNormalizer().normalize_provider(provider_result)
    drifted = result.model_dump(mode="json")
    drifted["artifact_id"] = _artifact("different")

    with pytest.raises(ValidationError, match="identity"):
        NormalizedClaimSet.model_validate(drifted)
