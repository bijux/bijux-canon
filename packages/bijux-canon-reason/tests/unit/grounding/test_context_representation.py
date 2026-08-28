# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Conflict, scope, uncertainty, and source-quality preservation tests."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json

from pydantic import ValidationError
import pytest

from bijux_canon_reason.grounding import (
    AnswerAnnotationKind,
    AtomicClaimNormalizer,
    CitationEvidence,
    CitationSourceDescriptor,
    CitationVerificationReport,
    ClaimCitationLinker,
    ClaimCitationSet,
    ClaimContextAnnotation,
    ClaimPresentationRole,
    ConflictRelationship,
    DeterministicCitationVerifier,
    EvidencePacketBuilder,
    EvidencePacketPolicy,
    GroundingContextService,
    ImmutableEvidenceLocator,
    JsonHttpResponse,
    NormalizedClaimSet,
    NuancedGroundingRepresentation,
    OpenAICompatibleStructuredSynthesizer,
    SourceQualityGrade,
    StructuredProviderConfiguration,
    create_answer_annotation,
    create_claim_conflict,
    create_claim_context,
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _artifact(value: str) -> str:
    return f"sha256:{_sha(value)}"


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


def _pipeline(
    statements: tuple[str, ...],
) -> tuple[
    NormalizedClaimSet,
    ClaimCitationSet,
    CitationVerificationReport,
    tuple[ClaimContextAnnotation, ...],
]:
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
        claim_set=claims,
        citation_set=citations,
        evidence_packet=packet,
        sources=tuple(sources),
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


def _with_role(
    context: ClaimContextAnnotation,
    role: ClaimPresentationRole,
    *,
    population_scope: tuple[str, ...] | None = None,
) -> ClaimContextAnnotation:
    return create_claim_context(
        claim_artifact_id=context.claim_artifact_id,
        population_scope=population_scope or context.population_scope,
        method_scope=context.method_scope,
        temporal_scope=context.temporal_scope,
        uncertainty=context.uncertainty,
        limitations=context.limitations,
        source_quality=context.source_quality,
        source_quality_basis=context.source_quality_basis,
        presentation_role=role,
    )


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
        "source quality=moderate",
        "[1]",
    ):
        assert retained in result.user_answer
    assert contexts[0].artifact_id not in result.user_answer


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
    assert "Unresolved conflicts and ambiguity:" in result.user_answer
    assert "[1, 2]" in result.user_answer


def test_scope_groups_merge_only_identical_explicit_dimensions() -> None:
    claims, citations, report, contexts = _pipeline(
        ("First scoped result.", "Second scoped result.", "Third scoped result.")
    )
    aligned = (
        _with_role(
            contexts[0],
            ClaimPresentationRole.finding,
            population_scope=("shared population",),
        ),
        create_claim_context(
            claim_artifact_id=contexts[1].claim_artifact_id,
            population_scope=("shared population",),
            method_scope=contexts[0].method_scope,
            temporal_scope=contexts[0].temporal_scope,
            uncertainty=contexts[1].uncertainty,
            limitations=contexts[1].limitations,
            source_quality=contexts[1].source_quality,
            source_quality_basis=contexts[1].source_quality_basis,
        ),
        contexts[2],
    )

    result = GroundingContextService().represent(
        claim_set=claims,
        citation_set=citations,
        verification_report=report,
        contexts=aligned,
    )

    assert tuple(len(group.claim_artifact_ids) for group in result.scope_groups) == (
        2,
        1,
    )
    assert result.user_answer.count("population=shared population") == 1


def test_material_counterevidence_cannot_be_omitted_or_majority_voted_away() -> None:
    claims, citations, report, contexts = _pipeline(
        ("The first source found preservation.", "The second source found loss.")
    )
    contextualized = (
        _with_role(contexts[0], ClaimPresentationRole.finding),
        _with_role(contexts[1], ClaimPresentationRole.counterevidence),
    )

    with pytest.raises(ValueError, match="material counterevidence conflict"):
        GroundingContextService().represent(
            claim_set=claims,
            citation_set=citations,
            verification_report=report,
            contexts=contextualized,
        )

    conflict = create_claim_conflict(
        relationship=ConflictRelationship.divergent,
        claim_artifact_ids=tuple(claim.artifact_id for claim in claims.claims),
        summary="Preservation and loss remain unresolved across the two sources.",
        scope_note="The source populations and methods are retained separately.",
    )
    result = GroundingContextService().represent(
        claim_set=claims,
        citation_set=citations,
        verification_report=report,
        contexts=contextualized,
        conflicts=(conflict,),
    )

    assert "Source-supported findings:" in result.user_answer
    assert "Cited counterevidence:" in result.user_answer
    assert conflict.summary in result.user_answer
    assert "[1, 2]" in result.user_answer
    assert all(link.artifact_id not in result.user_answer for link in citations.links)
    omitted = result.model_dump(mode="json")
    omitted["conflicts"] = []
    with pytest.raises(ValidationError, match="material counterevidence conflict"):
        NuancedGroundingRepresentation.model_validate(omitted)


def test_assumptions_and_interpretation_remain_explicitly_non_factual() -> None:
    claims, citations, report, contexts = _pipeline(("One supported result.",))
    annotations = (
        create_answer_annotation(
            kind=AnswerAnnotationKind.assumption,
            statement="Comparable sampling frames are assumed for this comparison.",
            basis_artifact_ids=(claims.artifact_id,),
        ),
        create_answer_annotation(
            kind=AnswerAnnotationKind.interpretation,
            statement="The product groups these records as a cautious comparison.",
            basis_artifact_ids=(claims.artifact_id,),
        ),
    )

    result = GroundingContextService().represent(
        claim_set=claims,
        citation_set=citations,
        verification_report=report,
        contexts=contexts,
        annotations=annotations,
    )

    assert "Assumptions (not source-supported facts):" in result.user_answer
    assert "Product interpretation (not source-supported facts):" in result.user_answer
    for annotation in annotations:
        line = next(
            item
            for item in result.user_answer.splitlines()
            if annotation.statement in item
        )
        assert "[" not in line


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
