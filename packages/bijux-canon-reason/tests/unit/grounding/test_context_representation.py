# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Conflict, scope, uncertainty, and source-quality preservation tests."""

from __future__ import annotations

import hashlib
import json

import pytest
from pydantic import ValidationError

from bijux_canon_reason.grounding import (
    AtomicClaimNormalizer,
    CitationEvidence,
    CitationSourceDescriptor,
    ClaimCitationLinker,
    ConflictRelationship,
    DeterministicCitationVerifier,
    EvidencePacketBuilder,
    EvidencePacketPolicy,
    GroundingContextService,
    ImmutableEvidenceLocator,
    JsonHttpResponse,
    NuancedGroundingRepresentation,
    OpenAICompatibleStructuredSynthesizer,
    SourceQualityGrade,
    StructuredProviderConfiguration,
    create_claim_conflict,
    create_claim_context,
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _artifact(value: str) -> str:
    return f"sha256:{_sha(value)}"


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


def _pipeline(statements: tuple[str, ...]):
    evidence_items = []
    sources = []
    candidate_claims = []
    for ordinal, statement in enumerate(statements, start=1):
        source_id = f"source-{ordinal}"
        source_content = f"Source {ordinal}: {statement}"
        source_uri = f"https://doi.org/10.1000/context-{ordinal}"
        evidence = CitationEvidence(
            artifact_id=_artifact(f"evidence:{ordinal}:{statement}"),
            chunk_artifact_id=_artifact(f"chunk:{ordinal}:{statement}"),
            retrieval_artifact_id=_artifact("retrieval"),
            document_id=f"document-{ordinal}",
            source_id=source_id,
            section_path=("results",),
            locator=ImmutableEvidenceLocator(
                artifact_id=_artifact(f"locator:{ordinal}"),
                source_artifact_id=_artifact(source_content),
                source_uri=source_uri,
                source_content_sha256=_sha(source_content),
                scheme="unicode-code-point",
                selectors=(("char_start", 10), ("char_end", 10 + len(statement))),
            ),
            exact_text=statement,
            exact_text_sha256=_sha(statement),
            rank=ordinal,
            relevance_score=1.0 / ordinal,
        )
        evidence_items.append(evidence)
        sources.append(
            CitationSourceDescriptor.create(
                source_id=source_id,
                title=f"Source title {ordinal}",
                canonical_uri=source_uri,
                doi=f"10.1000/context-{ordinal}",
                source_content_sha256=evidence.locator.source_content_sha256,
            )
        )
        candidate_claims.append(
            {
                "statement": statement,
                "citation_evidence_artifact_ids": [evidence.artifact_id],
                "polarity": "supports",
                "qualifier": "within the source",
                "scope": source_id,
            }
        )
    packet = EvidencePacketBuilder(
        EvidencePacketPolicy(
            token_budget=500,
            citation_budget=len(statements),
            claim_budget=len(statements),
            max_per_source=1,
            max_per_section=len(statements),
        )
    ).build(
        question_artifact_id=_artifact("question"),
        scope_artifact_id=_artifact("scope"),
        retrieval_trace_artifact_ids=(_artifact("trace"),),
        candidates=tuple(evidence_items),
    )
    candidate = {
        "schema_version": "bijux.canon.reason.provider_synthesis_candidate.v1",
        "outcome": "answered",
        "answer": " ".join(statements),
        "claims": candidate_claims,
        "limitations": ["Context must remain explicit."],
        "conflicts": [],
        "assumptions": [],
    }
    provider = OpenAICompatibleStructuredSynthesizer(
        StructuredProviderConfiguration(
            base_url="http://127.0.0.1:8000", model="test-model"
        ),
        credential_resolver=lambda: "secret",
        transport=_Transport(candidate),
    )
    synthesis = provider.synthesize(question="Question?", evidence_packet=packet)
    claims = AtomicClaimNormalizer().normalize_provider(synthesis)
    citations = ClaimCitationLinker().link(
        claim_set=claims, evidence_packet=packet, sources=tuple(sources)
    )
    report = DeterministicCitationVerifier().verify(
        claim_set=claims, citation_set=citations
    )
    contexts = tuple(
        create_claim_context(
            claim_artifact_id=claim.artifact_id,
            population_scope=(f"population {claim.ordinal}",),
            method_scope=(f"method {claim.ordinal}",),
            temporal_scope=(f"time window {claim.ordinal}",),
            uncertainty=("broader generalization is unverified",),
            limitations=("source-scoped result",),
            source_quality=SourceQualityGrade.moderate,
            source_quality_basis="peer-reviewed source; no independent appraisal",
        )
        for claim in claims.claims
    )
    return claims, citations, report, contexts


def test_claim_graph_and_answer_preserve_every_context_dimension() -> None:
    claims, citations, report, contexts = _pipeline(
        ("Ancient DNA fragments were shorter.",)
    )

    result = GroundingContextService().represent(
        claim_set=claims,
        citation_set=citations,
        verification_report=report,
        contexts=contexts,
    )
    restarted = NuancedGroundingRepresentation.model_validate_json(
        result.model_dump_json()
    )

    assert restarted == result
    assert result.nodes[0].context_artifact_id == contexts[0].artifact_id
    for retained in (
        "population 1",
        "method 1",
        "time window 1",
        "broader generalization is unverified",
        "source-scoped result",
        "source_quality=moderate",
        contexts[0].artifact_id,
    ):
        assert retained in result.user_answer


def test_divergent_claims_remain_separate_and_conflict_is_rendered() -> None:
    claims, citations, report, contexts = _pipeline(
        (
            "The first source reports contamination.",
            "The second source reports no contamination.",
        )
    )
    conflict = create_claim_conflict(
        relationship=ConflictRelationship.contradictory,
        claim_artifact_ids=tuple(claim.artifact_id for claim in claims.claims),
        summary="The admitted sources report contradictory contamination outcomes.",
        scope_note="The populations and methods differ, so the conflict is not adjudicated.",
    )

    result = GroundingContextService().represent(
        claim_set=claims,
        citation_set=citations,
        verification_report=report,
        contexts=contexts,
        conflicts=(conflict,),
    )

    assert len(result.nodes) == 2
    assert {node.claim_artifact_id for node in result.nodes} == set(
        conflict.claim_artifact_ids
    )
    assert conflict.summary in result.user_answer
    assert conflict.scope_note in result.user_answer
    assert "contradictory claims 1, 2" in result.user_answer


def test_missing_claim_context_fails_closed() -> None:
    claims, citations, report, contexts = _pipeline(
        ("First source result.", "Second source result.")
    )

    with pytest.raises(ValueError, match="every claim"):
        GroundingContextService().represent(
            claim_set=claims,
            citation_set=citations,
            verification_report=report,
            contexts=contexts[:1],
        )


def test_duplicate_claim_context_fails_closed() -> None:
    claims, citations, report, contexts = _pipeline(("One source result.",))

    with pytest.raises(ValueError, match="duplicate"):
        GroundingContextService().represent(
            claim_set=claims,
            citation_set=citations,
            verification_report=report,
            contexts=(contexts[0], contexts[0]),
        )


def test_conflict_referencing_unknown_claim_fails_closed() -> None:
    claims, citations, report, contexts = _pipeline(
        ("First source result.", "Second source result.")
    )
    conflict = create_claim_conflict(
        relationship=ConflictRelationship.divergent,
        claim_artifact_ids=(claims.claims[0].artifact_id, _artifact("unknown")),
        summary="Declared divergence.",
        scope_note="Different scopes.",
    )

    with pytest.raises(ValueError, match="unknown claim"):
        GroundingContextService().represent(
            claim_set=claims,
            citation_set=citations,
            verification_report=report,
            contexts=contexts,
            conflicts=(conflict,),
        )


def test_context_requires_all_scope_and_limitation_dimensions() -> None:
    claims, _, _, _ = _pipeline(("One source result.",))

    with pytest.raises(ValidationError, match="dimensions"):
        create_claim_context(
            claim_artifact_id=claims.claims[0].artifact_id,
            population_scope=(),
            method_scope=("method",),
            temporal_scope=("time",),
            uncertainty=("uncertain",),
            limitations=("limited",),
            source_quality=SourceQualityGrade.unknown,
            source_quality_basis="not assessed",
        )


def test_conflict_requires_two_distinct_claims() -> None:
    claims, _, _, _ = _pipeline(("One source result.",))

    with pytest.raises(ValidationError, match="distinct"):
        create_claim_conflict(
            relationship=ConflictRelationship.divergent,
            claim_artifact_ids=(claims.claims[0].artifact_id,),
            summary="Not enough claims.",
            scope_note="No comparison.",
        )


def test_representation_rejects_identity_drift() -> None:
    claims, citations, report, contexts = _pipeline(("One stable result.",))
    result = GroundingContextService().represent(
        claim_set=claims,
        citation_set=citations,
        verification_report=report,
        contexts=contexts,
    )
    drifted = result.model_dump(mode="json")
    drifted["artifact_id"] = _artifact("different")

    with pytest.raises(ValidationError, match="identity"):
        NuancedGroundingRepresentation.model_validate(drifted)
