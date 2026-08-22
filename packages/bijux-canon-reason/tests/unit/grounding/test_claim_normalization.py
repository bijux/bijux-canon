# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Atomic claim normalization, span, and failure tests."""

from __future__ import annotations

import hashlib
import json

from pydantic import ValidationError
import pytest

from bijux_canon_reason.grounding import (
    AtomicClaimNormalizer,
    AtomicClaimPolarity,
    CitationEvidence,
    ClaimConfidenceBasis,
    ClaimNormalizationError,
    ClaimNormalizationErrorCode,
    ClaimNormalizationOutcome,
    CredentialFreeSynthesizer,
    EvidencePacketBuilder,
    EvidencePacketPolicy,
    ImmutableEvidenceLocator,
    JsonHttpResponse,
    NormalizedClaimSet,
    OpenAICompatibleStructuredSynthesizer,
    StructuredProviderConfiguration,
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _artifact(value: str) -> str:
    return f"sha256:{_sha(value)}"


def _packet(*, empty: bool = False):
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
    def __init__(self, candidate: dict[str, object]) -> None:
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


def _provider_result(statement: str, answer: str):
    packet, evidence = _packet()
    candidate = {
        "schema_version": "bijux.canon.reason.provider_synthesis_candidate.v1",
        "outcome": "answered",
        "answer": answer,
        "claims": [
            {
                "statement": statement,
                "citation_evidence_artifact_ids": [evidence.artifact_id],
                "polarity": "opposes",
                "qualifier": "within the tested samples",
                "scope": "the source study",
            }
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
        claim.qualifier == "within the tested samples" for claim in result.claims
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


def test_noun_phrase_conjunction_is_not_split() -> None:
    statement = "DNA and RNA fragments degraded."
    provider_result, _ = _provider_result(statement, statement)

    result = AtomicClaimNormalizer().normalize_provider(provider_result)

    assert len(result.claims) == 1
    assert result.claims[0].statement == statement


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


def test_missing_provider_answer_span_fails_closed() -> None:
    provider_result, _ = _provider_result(
        "A candidate claim.", "An answer that omits the candidate."
    )

    with pytest.raises(ClaimNormalizationError) as caught:
        AtomicClaimNormalizer().normalize_provider(provider_result)

    assert caught.value.code is ClaimNormalizationErrorCode.answer_span_missing


def test_repeated_provider_answer_span_fails_as_ambiguous() -> None:
    provider_result, _ = _provider_result(
        "A repeated claim.", "A repeated claim. A repeated claim."
    )

    with pytest.raises(ClaimNormalizationError) as caught:
        AtomicClaimNormalizer().normalize_provider(provider_result)

    assert caught.value.code is ClaimNormalizationErrorCode.answer_span_ambiguous


def test_question_is_not_admitted_as_a_falsifiable_claim() -> None:
    provider_result, _ = _provider_result("What happened?", "What happened?")

    with pytest.raises(ClaimNormalizationError) as caught:
        AtomicClaimNormalizer().normalize_provider(provider_result)

    assert caught.value.code is ClaimNormalizationErrorCode.candidate_not_falsifiable


def test_insufficient_offline_synthesis_has_honest_empty_claim_set() -> None:
    packet, _ = _packet(empty=True)
    synthesis = CredentialFreeSynthesizer().synthesize(
        question="Unknown?", evidence_packet=packet
    )

    result = AtomicClaimNormalizer().normalize_credential_free(synthesis)

    assert result.outcome is ClaimNormalizationOutcome.no_claims
    assert result.claims == ()


def test_normalized_claim_set_is_deterministic_and_restart_safe() -> None:
    provider_result, _ = _provider_result("A stable claim.", "A stable claim.")
    normalizer = AtomicClaimNormalizer()

    first = normalizer.normalize_provider(provider_result)
    second = normalizer.normalize_provider(provider_result)
    restarted = NormalizedClaimSet.model_validate_json(first.model_dump_json())

    assert first == second == restarted


def test_normalized_claim_set_rejects_identity_drift() -> None:
    provider_result, _ = _provider_result("A stable claim.", "A stable claim.")
    result = AtomicClaimNormalizer().normalize_provider(provider_result)
    drifted = result.model_dump(mode="json")
    drifted["artifact_id"] = _artifact("different")

    with pytest.raises(ValidationError, match="identity"):
        NormalizedClaimSet.model_validate(drifted)
