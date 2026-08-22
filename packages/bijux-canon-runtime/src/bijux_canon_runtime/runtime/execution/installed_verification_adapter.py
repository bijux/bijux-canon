# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Installed verification of grounded answers and research traces."""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import ValidationError

from bijux_canon_agent.contracts import CausalDecisionEvent, ResearchCausalTrace
from bijux_canon_reason.grounding import (
    AtomicClaimNormalizer,
    CitationSourceDescriptor,
    CitationVerificationReport,
    ClaimCitationLinker,
    ClaimCitationSet,
    CredentialFreeSynthesis,
    DeterministicCitationVerifier,
    EvidencePacket,
    NormalizedClaimSet,
)
from bijux_canon_reason.research import (
    ConvergenceDecision,
    CounterevidencePlan,
    CounterevidenceSearchRun,
)
from bijux_canon_runtime.model.artifact import canonical_json_bytes
from bijux_canon_runtime.model.execution.request_plan import (
    ConcreteDagStep,
    DagOperation,
)
from bijux_canon_runtime.runtime.execution.installed_operation_adapters import (
    _bounded_output,
    _json_object,
)
from bijux_canon_runtime.runtime.execution.operation_dispatcher import (
    StepDispatchContext,
    StepDispatchError,
    StepOutputArtifact,
)


def _object(value: object, field: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise StepDispatchError(f"verification subject field is invalid: {field}")
    return value


def _strings(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise StepDispatchError(f"verification subject field is invalid: {field}")
    return tuple(value)


def _integer(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise StepDispatchError(f"verification subject field is invalid: {field}")
    return value


def _event(value: object) -> CausalDecisionEvent:
    raw = _object(value, "causal_event")
    try:
        event = CausalDecisionEvent(
            artifact_id=str(raw["artifact_id"]),
            sequence=_integer(raw["sequence"], "sequence"),
            state_before_artifact_id=str(raw["state_before_artifact_id"]),
            role=str(raw["role"]),
            operation=str(raw["operation"]),
            rationale=str(raw["rationale"]),
            observation_artifact_ids=_strings(
                raw["observation_artifact_ids"], "observation_artifact_ids"
            ),
            evidence_artifact_ids=_strings(
                raw["evidence_artifact_ids"], "evidence_artifact_ids"
            ),
            tool_decision_artifact_ids=_strings(
                raw["tool_decision_artifact_ids"], "tool_decision_artifact_ids"
            ),
            budget_decision_artifact_ids=_strings(
                raw["budget_decision_artifact_ids"], "budget_decision_artifact_ids"
            ),
            policy_artifact_ids=_strings(
                raw["policy_artifact_ids"], "policy_artifact_ids"
            ),
            output_artifact_ids=_strings(
                raw["output_artifact_ids"], "output_artifact_ids"
            ),
            operation_artifact_id=str(raw["operation_artifact_id"]),
            transition_artifact_id=str(raw["transition_artifact_id"]),
            state_after_artifact_id=str(raw["state_after_artifact_id"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise StepDispatchError("research causal event is invalid") from error
    recomputed = CausalDecisionEvent.create(
        sequence=event.sequence,
        state_before_artifact_id=event.state_before_artifact_id,
        role=event.role,
        operation=event.operation,
        rationale=event.rationale,
        observation_artifact_ids=event.observation_artifact_ids,
        evidence_artifact_ids=event.evidence_artifact_ids,
        tool_decision_artifact_ids=event.tool_decision_artifact_ids,
        budget_decision_artifact_ids=event.budget_decision_artifact_ids,
        policy_artifact_ids=event.policy_artifact_ids,
        output_artifact_ids=event.output_artifact_ids,
        operation_artifact_id=event.operation_artifact_id,
        transition_artifact_id=event.transition_artifact_id,
        state_after_artifact_id=event.state_after_artifact_id,
    )
    if event != recomputed:
        raise StepDispatchError("research causal event identity is invalid")
    return event


def _verify_claim_graph(subject: Mapping[str, object]) -> tuple[str, ...]:
    try:
        packet = EvidencePacket.model_validate(subject["evidence_packet"])
        synthesis = CredentialFreeSynthesis.model_validate(subject["synthesis"])
        claims = NormalizedClaimSet.model_validate(subject["claims"])
        citations = ClaimCitationSet.model_validate(subject["citations"])
        verification = CitationVerificationReport.model_validate(
            subject["citation_verification"]
        )
        raw_sources = subject["sources"]
        if not isinstance(raw_sources, list):
            raise TypeError
        sources = tuple(
            CitationSourceDescriptor.model_validate(item) for item in raw_sources
        )
    except (KeyError, TypeError, ValidationError) as error:
        raise StepDispatchError("grounded claim graph records are invalid") from error
    if subject.get("answer") != synthesis.answer_text:
        raise StepDispatchError("grounded answer differs from its synthesis")
    if synthesis.evidence_packet_artifact_id != packet.artifact_id:
        raise StepDispatchError("grounded synthesis refers to another evidence packet")
    if AtomicClaimNormalizer().normalize_credential_free(synthesis) != claims:
        raise StepDispatchError("grounded claim normalization is not reproducible")
    if (
        ClaimCitationLinker().link(
            claim_set=claims,
            evidence_packet=packet,
            sources=sources,
        )
        != citations
    ):
        raise StepDispatchError("grounded citation links are not reproducible")
    if (
        DeterministicCitationVerifier().verify(
            claim_set=claims,
            citation_set=citations,
        )
        != verification
    ):
        raise StepDispatchError("grounded citation verification is not reproducible")
    return (
        "evidence-packet-identity",
        "synthesis-answer-binding",
        "atomic-claim-normalization",
        "exact-citation-linking",
        "deterministic-entailment-verification",
    )


def _verify_research_trace(subject: Mapping[str, object]) -> tuple[str, ...]:
    try:
        plan = CounterevidencePlan.model_validate(subject["counterevidence_plan"])
        raw_run = subject.get("counterevidence_run")
        run = (
            None
            if raw_run is None
            else CounterevidenceSearchRun.model_validate(raw_run)
        )
        convergence = ConvergenceDecision.model_validate(subject["termination"])
        raw_events = subject["causal_events"]
        raw_trace = _object(subject["causal_trace"], "causal_trace")
        if not isinstance(raw_events, list):
            raise TypeError
        events = tuple(_event(item) for item in raw_events)
    except (KeyError, TypeError, ValidationError) as error:
        raise StepDispatchError("research trace records are invalid") from error
    if run is not None and run.plan_artifact_id != plan.artifact_id:
        raise StepDispatchError("counterevidence run refers to another plan")
    trace = ResearchCausalTrace.create(events)
    if raw_trace != {
        "artifact_id": trace.artifact_id,
        "event_artifact_ids": list(trace.event_artifact_ids),
        "head_artifact_id": trace.head_artifact_id,
    }:
        raise StepDispatchError("research causal trace identity is invalid")
    if not convergence.stop:
        raise StepDispatchError("research trace did not reach a terminal decision")
    candidate_ids = tuple(
        artifact_id
        for record in (() if run is None else run.records)
        for artifact_id in record.candidate_evidence_artifact_ids
    )
    if _strings(subject.get("opposition_candidates"), "opposition_candidates") != (
        candidate_ids
    ):
        raise StepDispatchError("research opposition candidates do not match search")
    return (
        "counterevidence-plan-identity",
        "counterevidence-search-lineage",
        "unclassified-opposition-preservation",
        "bounded-convergence-decision",
        "causal-event-chain",
    )


class CanonicalVerificationOperationAdapter:
    """Recompute all deterministic integrity checks for a terminal subject."""

    adapter_id = "bijux-canon-reason:runtime-verification:v1"
    adapter_version = "1.0"
    operation = DagOperation.VERIFY

    def execute(
        self,
        step: ConcreteDagStep,
        upstream_artifacts: tuple[StepOutputArtifact, ...],
        context: StepDispatchContext,
    ) -> tuple[StepOutputArtifact, ...]:
        context.raise_if_stopped()
        if len(upstream_artifacts) != 1:
            raise StepDispatchError("verification requires one terminal subject")
        subject_artifact = upstream_artifacts[0].artifact
        subject = _json_object(subject_artifact, upstream_artifacts[0].contract_id)
        if upstream_artifacts[0].contract_id == "reason.claim-graph.v1":
            checks = _verify_claim_graph(subject)
        elif upstream_artifacts[0].contract_id == "agent.research-trace.v1":
            checks = _verify_research_trace(subject)
        else:
            raise StepDispatchError("verification subject contract is unsupported")
        payload = canonical_json_bytes(
            {
                "checks": list(checks),
                "schema_version": "bijux.canon.reason.verification_receipt.v1",
                "status": "verified",
                "subject_artifact_id": str(subject_artifact.descriptor.artifact_id),
                "subject_contract_id": upstream_artifacts[0].contract_id,
                "subject_payload_sha256": str(
                    subject_artifact.descriptor.payload_sha256
                ),
            }
        )
        context.raise_if_stopped()
        return _bounded_output(
            step=step,
            contract_id="reason.verification-receipt.v1",
            media_type="application/json",
            payload=payload,
            upstream=upstream_artifacts,
        )


__all__ = ["CanonicalVerificationOperationAdapter"]
