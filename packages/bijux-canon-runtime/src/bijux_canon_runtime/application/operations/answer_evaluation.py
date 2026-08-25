# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Adapt one persisted Runtime RAG attempt into output-only evaluation records."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib

from bijux_canon_reason.evaluation import (
    SystemAnswerDisposition,
    SystemCitation,
    SystemClaim,
    SystemClaimDisposition,
    SystemOutput,
)
from bijux_canon_reason.grounding import (
    AtomicClaim,
    CitationSourceDescriptor,
    ClaimModality,
    EntailmentVerdict,
    GroundingAdmissionOutcome,
    LocalGroundedAnswer,
)
from bijux_canon_reason.grounding.provider_contracts import content_artifact_id
from bijux_canon_runtime.model.artifact import canonical_json_bytes
from bijux_canon_runtime.runtime.inspection import (
    InspectedArtifact,
    InspectedDagStep,
    InspectedRunStatus,
    InspectedStepStatus,
    RuntimeRunInspection,
)


class PersistedAnswerEvaluationError(ValueError):
    """A Runtime attempt cannot be proved to contain one coherent RAG answer."""


class PersistedAnswerEvaluationAdapter:
    """Create evaluation input from an inspected, content-addressed RAG graph."""

    def adapt(
        self,
        *,
        case_id: str,
        question: str,
        inspection: RuntimeRunInspection,
    ) -> SystemOutput:
        """Bind the exact completed Runtime attempt to its persisted answer graph."""

        if not case_id.strip() or not question.strip():
            raise PersistedAnswerEvaluationError(
                "evaluation case identity and question must not be empty"
            )
        if inspection.status is not InspectedRunStatus.COMPLETED:
            raise PersistedAnswerEvaluationError(
                "only a completed Runtime attempt can be evaluated"
            )
        if inspection.request_operation not in {"ask", "run"}:
            raise PersistedAnswerEvaluationError(
                "persisted answer evaluation requires an ask or run attempt"
            )
        graph_step, graph_artifact = _claim_graph(inspection)
        raw = graph_artifact.json_value
        if not isinstance(raw, dict) or (
            raw.get("schema_version") != "bijux.canon.reason.claim_graph.v1"
        ):
            raise PersistedAnswerEvaluationError(
                "persisted Reason claim graph schema is unsupported"
            )
        if raw.get("query") != question:
            raise PersistedAnswerEvaluationError(
                "persisted Reason question differs from evaluation truth"
            )

        grounded = _grounded_answer(raw)
        _validate_sources(raw, grounded)
        trace_identity = _trace_identity(
            inspection=inspection,
            graph_step=graph_step,
            graph_artifact=graph_artifact,
        )
        claims, citations = _admitted_output(grounded)
        disposition = _answer_disposition(grounded.outcome)
        abstention_reason = _abstention_reason(grounded)
        answer = (
            ""
            if disposition is SystemAnswerDisposition.abstained
            else grounded.answer_text
        )
        output_payload = {
            "schema_version": "bijux.canon.evaluation.runtime-system-output.v1",
            "case_id": case_id,
            "runtime_run_id": inspection.run_id,
            "runtime_attempt_id": inspection.selected_attempt_id,
            "claim_graph_artifact_id": str(graph_artifact.artifact_id),
            "answer": answer,
            "disposition": disposition.value,
            "claims": tuple(item.model_dump(mode="json") for item in claims),
            "citations": tuple(item.model_dump(mode="json") for item in citations),
            "abstention_reason": abstention_reason,
            "trace_identity_sha256": trace_identity,
        }
        return SystemOutput(
            output_id=content_artifact_id(output_payload),
            case_id=case_id,
            runtime_run_id=inspection.run_id,
            runtime_attempt_id=inspection.selected_attempt_id,
            answer=answer,
            disposition=disposition,
            claims=claims,
            citations=citations,
            abstention_reason=abstention_reason,
            trace_identity_sha256=trace_identity,
        )


def _claim_graph(
    inspection: RuntimeRunInspection,
) -> tuple[InspectedDagStep, InspectedArtifact]:
    artifacts = {item.artifact_id: item for item in inspection.artifacts}
    matches: list[tuple[InspectedDagStep, InspectedArtifact]] = []
    for step in inspection.steps:
        if (
            step.operation != "reason"
            or step.status is not InspectedStepStatus.COMPLETED
            or step.attempt_id != inspection.selected_attempt_id
        ):
            continue
        for artifact_id in step.output_artifact_ids:
            artifact = artifacts.get(artifact_id)
            if artifact is not None and artifact.schema_id == "reason.claim-graph.v1":
                matches.append((step, artifact))
    if len(matches) != 1:
        raise PersistedAnswerEvaluationError(
            "completed Runtime attempt must contain exactly one Reason claim graph"
        )
    return matches[0]


def _grounded_answer(raw: Mapping[str, object]) -> LocalGroundedAnswer:
    try:
        return LocalGroundedAnswer.model_validate(
            {
                "artifact_id": raw.get("grounded_answer_artifact_id"),
                "answer_text": raw.get("answer"),
                "outcome": raw.get("answer_disposition"),
                "synthesis": raw.get("synthesis"),
                "claims": raw.get("claims"),
                "citations": raw.get("citations"),
                "citation_presentation": raw.get("citation_presentation"),
                "verification": raw.get("citation_verification"),
                "admission": raw.get("grounding_admission"),
                "contextualized": raw.get("contextualized"),
                "evidence_state": raw.get("evidence_state"),
            }
        )
    except ValueError as error:
        raise PersistedAnswerEvaluationError(
            "persisted Reason answer graph fails content or lineage validation"
        ) from error


def _validate_sources(raw: Mapping[str, object], grounded: LocalGroundedAnswer) -> None:
    raw_sources = raw.get("sources")
    if not isinstance(raw_sources, list):
        raise PersistedAnswerEvaluationError(
            "persisted Reason answer has no source authority"
        )
    try:
        sources = tuple(
            CitationSourceDescriptor.model_validate(item) for item in raw_sources
        )
    except ValueError as error:
        raise PersistedAnswerEvaluationError(
            "persisted Reason source authority is invalid"
        ) from error
    source_ids = tuple(
        item.artifact_id for item in sorted(sources, key=lambda item: item.source_id)
    )
    if len({item.source_id for item in sources}) != len(sources) or (
        source_ids != grounded.verification.source_descriptor_artifact_ids
    ):
        raise PersistedAnswerEvaluationError(
            "persisted Reason source authority differs from citation verification"
        )
    by_id = {item.source_id: item for item in sources}
    for link in grounded.citations.links:
        source = by_id.get(link.source_id)
        if source is None or source.artifact_id != link.source_descriptor_artifact_id:
            raise PersistedAnswerEvaluationError(
                "persisted citation link is not reachable from source authority"
            )


def _trace_identity(
    *,
    inspection: RuntimeRunInspection,
    graph_step: InspectedDagStep,
    graph_artifact: InspectedArtifact,
) -> str:
    payload = {
        "schema_version": "bijux.canon.evaluation.runtime-trace-binding.v1",
        "run_id": inspection.run_id,
        "attempt_id": inspection.selected_attempt_id,
        "request_id": inspection.request_id,
        "plan_sha256": inspection.plan_sha256,
        "reason_step_id": graph_step.step_id,
        "claim_graph_artifact_id": str(graph_artifact.artifact_id),
        "claim_graph_payload_sha256": graph_artifact.payload_sha256,
        "event_artifact_ids": [str(item.artifact_id) for item in inspection.events],
    }
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def _admitted_output(
    grounded: LocalGroundedAnswer,
) -> tuple[tuple[SystemClaim, ...], tuple[SystemCitation, ...]]:
    admitted = set(grounded.admission.admitted_claim_artifact_ids)
    verification_by_claim = {
        item.claim_artifact_id: item for item in grounded.verification.claims
    }
    if any(
        claim_id not in verification_by_claim
        or verification_by_claim[claim_id].verdict
        is not EntailmentVerdict.direct_support
        for claim_id in admitted
    ):
        raise PersistedAnswerEvaluationError(
            "grounding admission exposes a claim without verified direct support"
        )
    admitted_claims = tuple(
        item for item in grounded.claims.claims if item.artifact_id in admitted
    )
    if {item.artifact_id for item in admitted_claims} != admitted:
        raise PersistedAnswerEvaluationError(
            "grounding admission names a missing normalized claim"
        )
    admitted_links = tuple(
        item
        for item in grounded.citations.links
        if item.claim_artifact_id in admitted
        and item.artifact_id in grounded.admission.admitted_citation_link_artifact_ids
    )
    if {item.artifact_id for item in admitted_links} != set(
        grounded.admission.admitted_citation_link_artifact_ids
    ):
        raise PersistedAnswerEvaluationError(
            "grounding admission names a missing citation link"
        )
    presentation_by_evidence = {
        item.citation_evidence_artifact_id: item
        for item in grounded.citation_presentation.entries
    }
    admitted_evidence = tuple(
        dict.fromkeys(item.citation_evidence_artifact_id for item in admitted_links)
    )
    try:
        citations = tuple(
            SystemCitation(
                schema_version="bijux.canon.evaluation.system-citation.v2",
                citation_id=presentation_by_evidence[evidence_id].artifact_id,
                source_id=presentation_by_evidence[evidence_id].source_id,
                source_uri=presentation_by_evidence[evidence_id].source_uri,
                source_sha256=presentation_by_evidence[
                    evidence_id
                ].source_content_sha256,
                locator_id=presentation_by_evidence[evidence_id].locator_artifact_id,
                exact_text_sha256=presentation_by_evidence[
                    evidence_id
                ].exact_quote_sha256,
                character_start=0,
                character_end=len(presentation_by_evidence[evidence_id].exact_quote),
                exact_text=presentation_by_evidence[evidence_id].exact_quote,
                chunk_id=presentation_by_evidence[evidence_id].chunk_artifact_id,
            )
            for evidence_id in admitted_evidence
        )
    except KeyError as error:
        raise PersistedAnswerEvaluationError(
            "admitted citation has no exact presentation record"
        ) from error
    citation_id_by_evidence = {
        evidence_id: presentation_by_evidence[evidence_id].artifact_id
        for evidence_id in admitted_evidence
    }
    links_by_claim = {
        claim.artifact_id: tuple(
            link
            for link in admitted_links
            if link.claim_artifact_id == claim.artifact_id
        )
        for claim in admitted_claims
    }
    claims = tuple(
        SystemClaim(
            claim_id=claim.artifact_id,
            statement=claim.statement,
            disposition=_claim_disposition(claim),
            citation_ids=tuple(
                dict.fromkeys(
                    citation_id_by_evidence[link.citation_evidence_artifact_id]
                    for link in links_by_claim[claim.artifact_id]
                )
            ),
        )
        for claim in admitted_claims
    )
    return claims, citations


def _claim_disposition(claim: AtomicClaim) -> SystemClaimDisposition:
    qualification = claim.qualification
    qualified = bool(
        qualification.modality is not ClaimModality.asserted
        or qualification.population_scope
        or qualification.temporal_scope
        or qualification.quantitative_scope
        or qualification.source_qualifier
    )
    return (
        SystemClaimDisposition.qualified
        if qualified
        else SystemClaimDisposition.asserted
    )


def _answer_disposition(
    outcome: GroundingAdmissionOutcome,
) -> SystemAnswerDisposition:
    return {
        GroundingAdmissionOutcome.admitted: SystemAnswerDisposition.answered,
        GroundingAdmissionOutcome.partially_admitted: (
            SystemAnswerDisposition.partially_abstained
        ),
        GroundingAdmissionOutcome.abstained: SystemAnswerDisposition.abstained,
    }[outcome]


def _abstention_reason(grounded: LocalGroundedAnswer) -> str | None:
    if grounded.outcome is GroundingAdmissionOutcome.admitted:
        return None
    return " ".join(
        f"{item.detail} Next action: {item.required_action}"
        for item in grounded.admission.evidence_gaps
    )


__all__ = [
    "PersistedAnswerEvaluationAdapter",
    "PersistedAnswerEvaluationError",
]
