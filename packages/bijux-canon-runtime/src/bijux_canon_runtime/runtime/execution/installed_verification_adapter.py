# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Installed verification of grounded answers and research traces."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from pydantic import ValidationError

from bijux_canon_agent.application import (
    InstalledResearchConvergence,
    InstalledResearchTerminalKind,
    InstalledResearchTerminalOutcome,
    RemainingResearchWork,
)
from bijux_canon_agent.contracts import (
    BudgetAction,
    BudgetDecision,
    BudgetDimensions,
    CancellationSignal,
    CausalDecisionEvent,
    ResearchBudgetLedger,
    ResearchBudgetPolicy,
    ResearchCausalTrace,
    ResearchTool,
    ResearchToolDescriptor,
    ResearchToolOperation,
    ToolExecutionRecord,
    ToolExecutionStatus,
    ToolGrant,
    ToolInvocation,
    ToolPolicy,
    ToolPolicyAction,
    ToolPolicyDecision,
    ToolPolicyReason,
    ToolReplayPolicy,
)
from bijux_canon_reason.grounding import (
    AtomicClaimNormalizer,
    CitationPresentation,
    CitationPresentationService,
    CitationSourceDescriptor,
    CitationVerificationReport,
    ClaimCitationLinker,
    ClaimCitationSet,
    CredentialFreeSynthesis,
    DeterministicCitationVerifier,
    EvidencePacket,
    GroundingAdmissionDecision,
    GroundingAdmissionService,
    GroundingEvidenceState,
    LocalGroundedAnswer,
    NormalizedClaimSet,
    NuancedGroundingRepresentation,
    render_grounded_answer,
)
from bijux_canon_reason.grounding.provider_contracts import content_artifact_id
from bijux_canon_reason.research import (
    AnswerRequirementPlan,
    CandidateAdjudicationReport,
    ConvergenceDecision,
    CounterevidencePlan,
    CounterevidenceSearchRun,
    ResearchAnswerRevision,
    ResearchCandidateClassification,
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


def _boolean(value: object, field: str) -> bool:
    if not isinstance(value, bool):
        raise StepDispatchError(f"verification subject field is invalid: {field}")
    return value


def _cancellation_signal(value: object) -> CancellationSignal | None:
    if value is None:
        return None
    raw = _object(value, "cancellation_signal")
    requested = raw.get("requested")
    reason = raw.get("reason")
    request_artifact_id = raw.get("request_artifact_id")
    if (
        requested is not True
        or not isinstance(reason, str)
        or not isinstance(request_artifact_id, str)
    ):
        raise StepDispatchError("research cancellation signal is invalid")
    signal = CancellationSignal(
        artifact_id=str(raw.get("artifact_id")),
        requested=True,
        reason=reason,
        request_artifact_id=request_artifact_id,
    )
    if signal != CancellationSignal.active(
        reason=reason,
        request_artifact_id=request_artifact_id,
    ):
        raise StepDispatchError("research cancellation identity is invalid")
    return signal


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


def _budget_dimensions(value: object, field: str) -> BudgetDimensions:
    raw = _object(value, field)
    expected = set(BudgetDimensions().payload())
    if set(raw) != expected:
        raise StepDispatchError(f"verification subject field is invalid: {field}")
    return BudgetDimensions(
        **{name: _integer(raw[name], f"{field}.{name}") for name in expected}
    )


def _budget_policy(value: object) -> ResearchBudgetPolicy:
    raw = _object(value, "budget_policy")
    raw_roles = _object(raw.get("role_limits"), "budget role_limits")
    try:
        policy = ResearchBudgetPolicy(
            plan_sha256=str(raw["plan_sha256"]),
            global_limits=_budget_dimensions(
                raw["global_limits"], "budget global_limits"
            ),
            role_limits={
                role: _budget_dimensions(limits, f"budget role {role}")
                for role, limits in raw_roles.items()
            },
        )
    except (KeyError, TypeError, ValueError) as error:
        raise StepDispatchError("research budget policy is invalid") from error
    if raw.get("artifact_id") != policy.artifact_id:
        raise StepDispatchError("research budget policy identity is invalid")
    return policy


def _budget_decision(value: object) -> BudgetDecision:
    raw = _object(value, "budget_decision")
    try:
        decision = BudgetDecision(
            artifact_id=str(raw["artifact_id"]),
            sequence=_integer(raw["sequence"], "budget sequence"),
            policy_artifact_id=str(raw["policy_artifact_id"]),
            role=str(raw["role"]),
            label=str(raw["label"]),
            action=BudgetAction(str(raw["action"])),
            charge=_budget_dimensions(raw["charge"], "budget charge"),
            global_usage=_budget_dimensions(raw["global_usage"], "budget global_usage"),
            role_usage=_budget_dimensions(raw["role_usage"], "budget role_usage"),
            exhausted_dimensions=_strings(
                raw["exhausted_dimensions"], "budget exhausted_dimensions"
            ),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise StepDispatchError("research budget decision is invalid") from error
    if decision != BudgetDecision.create(
        sequence=decision.sequence,
        policy_artifact_id=decision.policy_artifact_id,
        role=decision.role,
        label=decision.label,
        action=decision.action,
        charge=decision.charge,
        global_usage=decision.global_usage,
        role_usage=decision.role_usage,
        exhausted_dimensions=decision.exhausted_dimensions,
    ):
        raise StepDispatchError("research budget decision identity is invalid")
    return decision


def _tool_policy(value: object, *, plan_sha256: str) -> ToolPolicy:
    raw = _object(value, "tool_policy")
    raw_grants = raw.get("grants")
    if not isinstance(raw_grants, list):
        raise StepDispatchError("research tool policy grants are invalid")
    try:
        grants = tuple(
            ToolGrant(
                tool=ResearchTool(str(grant["tool"])),
                operation=ResearchToolOperation(str(grant["operation"])),
                corpus_generation=str(grant["corpus_generation"]),
                index_generation=str(grant["index_generation"]),
                scope=_strings(grant["scope"], "tool grant scope"),
                filesystem_roots=_strings(
                    grant["filesystem_roots"], "tool grant filesystem_roots"
                ),
                max_calls=_integer(grant["max_calls"], "tool grant max_calls"),
                timeout_ms=_integer(grant["timeout_ms"], "tool grant timeout_ms"),
            )
            for grant in (_object(item, "tool grant") for item in raw_grants)
        )
        policy = ToolPolicy(
            plan_sha256=str(raw["plan_sha256"]),
            grants=grants,
            denied_tools=_strings(raw["denied_tools"], "denied_tools"),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise StepDispatchError("research tool policy is invalid") from error
    if (
        policy.plan_sha256 != plan_sha256
        or raw.get("artifact_id") != policy.artifact_id
        or raw.get("policy_sha256") != policy.policy_sha256
        or raw.get("default_action") != "deny"
    ):
        raise StepDispatchError("research tool policy binding is invalid")
    return policy


def _tool_descriptor(value: object) -> ResearchToolDescriptor:
    raw = _object(value, "tool_descriptor")
    try:
        descriptor = ResearchToolDescriptor(
            tool=ResearchTool(str(raw["tool"])),
            operation=ResearchToolOperation(str(raw["operation"])),
            version=str(raw["version"]),
            input_schema_id=str(raw["input_schema_id"]),
            output_schema_id=str(raw["output_schema_id"]),
            capability=str(raw["capability"]),
            owner_distribution=str(raw["owner_distribution"]),
            implementation=str(raw["implementation"]),
            replay_policy=ToolReplayPolicy(str(raw["replay_policy"])),
            cost_units=_integer(raw["cost_units"], "tool descriptor cost_units"),
            safe_summary_fields=_strings(
                raw["safe_summary_fields"], "tool descriptor safe_summary_fields"
            ),
            supports_cancellation=_boolean(
                raw["supports_cancellation"], "tool descriptor supports_cancellation"
            ),
            read_only=_boolean(raw["read_only"], "tool descriptor read_only"),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise StepDispatchError("research tool descriptor is invalid") from error
    if raw.get("artifact_id") != descriptor.artifact_id:
        raise StepDispatchError("research tool descriptor identity is invalid")
    return descriptor


def _tool_invocation(value: object) -> ToolInvocation:
    raw = _object(value, "tool invocation")
    try:
        return ToolInvocation(
            tool=str(raw["tool"]),
            operation=str(raw["operation"]),
            plan_sha256=str(raw["plan_sha256"]),
            request_sha256=str(raw["request_sha256"]),
            corpus_generation=str(raw["corpus_generation"]),
            index_generation=str(raw["index_generation"]),
            scope=_strings(raw["scope"], "tool invocation scope"),
            filesystem_paths=_strings(
                raw["filesystem_paths"], "tool invocation filesystem_paths"
            ),
            timeout_ms=_integer(raw["timeout_ms"], "tool invocation timeout_ms"),
            tool_version=str(raw["tool_version"]),
            input_schema_id=str(raw["input_schema_id"]),
            output_schema_id=str(raw["output_schema_id"]),
            capability=str(raw["capability"]),
            cost_units=_integer(raw["cost_units"], "tool invocation cost_units"),
            idempotency_key=(
                None if raw["idempotency_key"] is None else str(raw["idempotency_key"])
            ),
            replay_requested=_boolean(
                raw["replay_requested"], "tool invocation replay_requested"
            ),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise StepDispatchError("research tool invocation is invalid") from error


def _tool_decision(value: object) -> ToolPolicyDecision:
    raw = _object(value, "tool decision")
    try:
        decision = ToolPolicyDecision(
            artifact_id=str(raw["artifact_id"]),
            sequence=_integer(raw["sequence"], "tool decision sequence"),
            action=ToolPolicyAction(str(raw["action"])),
            reason=ToolPolicyReason(str(raw["reason"])),
            policy_sha256=str(raw["policy_sha256"]),
            invocation=_tool_invocation(raw["invocation"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise StepDispatchError("research tool decision is invalid") from error
    expected = ToolPolicyDecision.create(
        sequence=decision.sequence,
        action=decision.action,
        reason=decision.reason,
        policy_sha256=decision.policy_sha256,
        invocation=decision.invocation,
    )
    if decision != expected:
        raise StepDispatchError("research tool decision identity is invalid")
    return decision


def _tool_execution_record(value: object) -> ToolExecutionRecord:
    raw = _object(value, "tool execution record")
    try:
        return ToolExecutionRecord(
            artifact_id=str(raw["artifact_id"]),
            sequence=_integer(raw["sequence"], "tool execution sequence"),
            descriptor_artifact_id=str(raw["descriptor_artifact_id"]),
            policy_decision_artifact_id=str(raw["policy_decision_artifact_id"]),
            request_sha256=str(raw["request_sha256"]),
            result_artifact_id=(
                None
                if raw["result_artifact_id"] is None
                else str(raw["result_artifact_id"])
            ),
            status=ToolExecutionStatus(str(raw["status"])),
            safe_summary=_object(raw["safe_summary"], "tool execution safe_summary"),
            idempotency_key=str(raw["idempotency_key"]),
            replay_source_artifact_id=(
                None
                if raw["replay_source_artifact_id"] is None
                else str(raw["replay_source_artifact_id"])
            ),
            cancellation_artifact_id=(
                None
                if raw["cancellation_artifact_id"] is None
                else str(raw["cancellation_artifact_id"])
            ),
            failure_class=(
                None if raw["failure_class"] is None else str(raw["failure_class"])
            ),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise StepDispatchError("research tool execution record is invalid") from error


def _verify_claim_graph(
    subject: Mapping[str, object], *, subject_dependency_ids: frozenset[str]
) -> tuple[str, ...]:
    try:
        packet = EvidencePacket.model_validate(subject["evidence_packet"])
        synthesis = CredentialFreeSynthesis.model_validate(subject["synthesis"])
        claims = NormalizedClaimSet.model_validate(subject["claims"])
        citations = ClaimCitationSet.model_validate(subject["citations"])
        citation_presentation = CitationPresentation.model_validate(
            subject["citation_presentation"]
        )
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
    answer = subject.get("answer")
    if not isinstance(answer, str):
        raise StepDispatchError("grounded answer is invalid")
    evidence_set_artifact_id = subject.get("evidence_set_artifact_id")
    if (
        not isinstance(evidence_set_artifact_id, str)
        or evidence_set_artifact_id not in subject_dependency_ids
        or evidence_set_artifact_id not in packet.retrieval_trace_artifact_ids
        or any(
            evidence.retrieval_artifact_id != evidence_set_artifact_id
            for evidence in packet.selected
        )
    ):
        raise StepDispatchError(
            "grounded citations are not bound to the persisted retrieval artifact"
        )
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
    if CitationPresentationService().present(citations) != citation_presentation:
        raise StepDispatchError("grounded citation presentation is not reproducible")
    if (
        DeterministicCitationVerifier().verify(
            claim_set=claims,
            citation_set=citations,
            evidence_packet=packet,
            sources=sources,
        )
        != verification
    ):
        raise StepDispatchError("grounded citation verification is not reproducible")
    if "grounded_answer_artifact_id" in subject:
        try:
            admission = GroundingAdmissionDecision.model_validate(
                subject["grounding_admission"]
            )
            evidence_state = GroundingEvidenceState.model_validate(
                subject["evidence_state"]
            )
            contextualized = NuancedGroundingRepresentation.model_validate(
                subject["contextualized"]
            )
            expected_answer = render_grounded_answer(
                synthesis=synthesis,
                claims=claims,
                citations=citations,
                admission=admission,
                citation_presentation=citation_presentation,
                contextualized=contextualized,
            )
            if answer != expected_answer:
                raise StepDispatchError("grounded answer differs from its admission")
            if subject.get("answer_disposition") != admission.outcome.value:
                raise StepDispatchError("grounded answer disposition differs")
            LocalGroundedAnswer(
                artifact_id=str(subject["grounded_answer_artifact_id"]),
                answer_text=answer,
                outcome=admission.outcome,
                synthesis=synthesis,
                claims=claims,
                citations=citations,
                citation_presentation=citation_presentation,
                verification=verification,
                admission=admission,
                contextualized=contextualized,
                evidence_state=evidence_state,
            )
        except (KeyError, TypeError, ValidationError) as error:
            raise StepDispatchError("local grounded answer is invalid") from error
        if (
            GroundingAdmissionService().decide(
                claim_set=claims,
                citation_set=citations,
                verification_report=verification,
                request_status=admission.request_status,
                evidence_state=evidence_state,
            )
            != admission
        ):
            raise StepDispatchError("grounding admission is not reproducible")
    elif answer != synthesis.answer_text:
        raise StepDispatchError("grounded answer differs from its synthesis")
    return (
        "evidence-packet-identity",
        "persisted-retrieval-artifact-binding",
        "grounding-admission-binding",
        "atomic-claim-normalization",
        "exact-citation-linking",
        "human-usable-citation-presentation",
        "deterministic-entailment-verification",
    )


@dataclass(frozen=True, slots=True)
class _ResearchTraceRecords:
    requirements: AnswerRequirementPlan
    plan: CounterevidencePlan
    run: CounterevidenceSearchRun | None
    convergence: ConvergenceDecision | InstalledResearchConvergence
    research_outcome: InstalledResearchTerminalOutcome
    remaining_work: RemainingResearchWork
    cancellation_signal: CancellationSignal | None
    events: tuple[CausalDecisionEvent, ...]
    raw_trace: dict[str, object]
    raw_state: dict[str, object]
    budget_policy: ResearchBudgetPolicy
    budget_decisions: tuple[BudgetDecision, ...]
    budget: ResearchBudgetLedger
    tool_policy: ToolPolicy
    tool_descriptors: tuple[ResearchToolDescriptor, ...]
    tool_decisions: tuple[ToolPolicyDecision, ...]
    tool_records: tuple[ToolExecutionRecord, ...]


def _research_trace_records(subject: Mapping[str, object]) -> _ResearchTraceRecords:
    try:
        requirements = AnswerRequirementPlan.model_validate(
            subject["answer_requirement_plan"]
        )
        plan = CounterevidencePlan.model_validate(subject["counterevidence_plan"])
        raw_run = subject.get("counterevidence_run")
        run = (
            None
            if raw_run is None
            else CounterevidenceSearchRun.model_validate(raw_run)
        )
        raw_termination = _object(subject["termination"], "termination")
        convergence = (
            ConvergenceDecision.model_validate(raw_termination)
            if str(raw_termination.get("schema_version", "")).startswith(
                "bijux.canon.reason.convergence_decision."
            )
            else InstalledResearchConvergence(
                artifact_id=str(raw_termination["artifact_id"]),
                outcome=str(raw_termination["outcome"]),
                stop=_boolean(raw_termination["stop"], "termination.stop"),
                record=raw_termination,
            )
        )
        raw_research_outcome = _object(subject["research_outcome"], "research_outcome")
        raw_remaining_work = _object(
            raw_research_outcome["remaining_work"], "remaining_work"
        )
        remaining_work = RemainingResearchWork(
            artifact_id=str(raw_remaining_work["artifact_id"]),
            unsatisfied_requirement_artifact_ids=_strings(
                raw_remaining_work["unsatisfied_requirement_artifact_ids"],
                "unsatisfied_requirement_artifact_ids",
            ),
            unresolved_evidence_artifact_ids=_strings(
                raw_remaining_work["unresolved_evidence_artifact_ids"],
                "unresolved_evidence_artifact_ids",
            ),
            unresolved_gap_artifact_ids=_strings(
                raw_remaining_work["unresolved_gap_artifact_ids"],
                "unresolved_gap_artifact_ids",
            ),
            unsearched_important_claim_artifact_ids=_strings(
                raw_remaining_work["unsearched_important_claim_artifact_ids"],
                "unsearched_important_claim_artifact_ids",
            ),
            descriptions=_strings(
                raw_remaining_work["descriptions"], "remaining_work descriptions"
            ),
        )
        research_outcome = InstalledResearchTerminalOutcome(
            artifact_id=str(raw_research_outcome["artifact_id"]),
            kind=InstalledResearchTerminalKind(str(raw_research_outcome["kind"])),
            convergence_artifact_id=str(
                raw_research_outcome["convergence_artifact_id"]
            ),
            convergence_outcome=str(raw_research_outcome["convergence_outcome"]),
            remaining_work=remaining_work,
            exhausted_budget_dimensions=_strings(
                raw_research_outcome["exhausted_budget_dimensions"],
                "exhausted_budget_dimensions",
            ),
            cancellation_artifact_id=(
                None
                if raw_research_outcome["cancellation_artifact_id"] is None
                else str(raw_research_outcome["cancellation_artifact_id"])
            ),
            failure_artifact_ids=_strings(
                raw_research_outcome["failure_artifact_ids"],
                "failure_artifact_ids",
            ),
        )
        cancellation_signal = _cancellation_signal(subject["cancellation_signal"])
        raw_events = subject["causal_events"]
        raw_trace = _object(subject["causal_trace"], "causal_trace")
        raw_state = _object(subject["research_state"], "research_state")
        budget_policy = _budget_policy(subject["budget_policy"])
        raw_budget_decisions = subject["budget_decisions"]
        if not isinstance(raw_events, list) or not isinstance(
            raw_budget_decisions, list
        ):
            raise TypeError
        events = tuple(_event(item) for item in raw_events)
        budget_decisions = tuple(
            _budget_decision(item) for item in raw_budget_decisions
        )
        budget = ResearchBudgetLedger(budget_policy)
        budget.restore(budget_decisions)
        tool_policy = _tool_policy(
            subject["tool_policy"],
            plan_sha256=budget_policy.plan_sha256,
        )
        raw_tool_descriptors = subject["tool_descriptors"]
        raw_tool_decisions = subject["tool_decisions"]
        raw_tool_records = subject["tool_execution_records"]
        if (
            not isinstance(raw_tool_descriptors, list)
            or not isinstance(raw_tool_decisions, list)
            or not isinstance(raw_tool_records, list)
        ):
            raise TypeError
        tool_descriptors = tuple(
            _tool_descriptor(item) for item in raw_tool_descriptors
        )
        tool_decisions = tuple(_tool_decision(item) for item in raw_tool_decisions)
        tool_records = tuple(_tool_execution_record(item) for item in raw_tool_records)
        return _ResearchTraceRecords(
            requirements=requirements,
            plan=plan,
            run=run,
            convergence=convergence,
            research_outcome=research_outcome,
            remaining_work=remaining_work,
            cancellation_signal=cancellation_signal,
            events=events,
            raw_trace=raw_trace,
            raw_state=raw_state,
            budget_policy=budget_policy,
            budget_decisions=budget_decisions,
            budget=budget,
            tool_policy=tool_policy,
            tool_descriptors=tool_descriptors,
            tool_decisions=tool_decisions,
            tool_records=tool_records,
        )
    except (KeyError, TypeError, ValueError, ValidationError) as error:
        raise StepDispatchError("research trace records are invalid") from error


def _verify_research_terminal(
    subject: Mapping[str, object], records: _ResearchTraceRecords
) -> None:
    if records.run is not None and (
        records.run.plan_artifact_id != records.plan.artifact_id
    ):
        raise StepDispatchError("counterevidence run refers to another plan")
    convergence = records.convergence
    if isinstance(convergence, InstalledResearchConvergence):
        raw_convergence = dict(convergence.record)
        schema_version = raw_convergence.get("schema_version")
        expected_outcome = (
            {
                "bijux.canon.agent.budget_convergence.v1": "budget_exhausted",
                "bijux.canon.agent.cancellation_convergence.v1": "cancelled",
            }.get(schema_version)
            if isinstance(schema_version, str)
            else None
        )
        identity_payload = {
            key: value for key, value in raw_convergence.items() if key != "artifact_id"
        }
        if (
            expected_outcome is None
            or convergence.outcome != expected_outcome
            or not convergence.stop
            or convergence.artifact_id != content_artifact_id(identity_payload)
        ):
            raise StepDispatchError("Agent terminal convergence record is invalid")
    convergence_outcome = (
        convergence.outcome
        if isinstance(convergence, InstalledResearchConvergence)
        else convergence.outcome.value
    )
    outcome = records.research_outcome
    if (
        outcome.convergence_artifact_id != convergence.artifact_id
        or outcome.convergence_outcome != convergence_outcome
        or subject.get("status") != outcome.kind.value
        or subject.get("convergence_status") != convergence_outcome
    ):
        raise StepDispatchError("research terminal outcome differs from convergence")
    cancellation = records.cancellation_signal
    if cancellation is not None:
        if outcome.cancellation_artifact_id != cancellation.artifact_id:
            raise StepDispatchError("research cancellation identity is invalid")
    elif outcome.cancellation_artifact_id is not None:
        raise StepDispatchError("research cancellation signal is missing")


def _verify_targeted_search(
    subject: Mapping[str, object], plan: CounterevidencePlan
) -> None:
    raw_targeted = subject.get("targeted_search_plan")
    if not isinstance(raw_targeted, dict):
        raise StepDispatchError("targeted search plan is missing or invalid")
    if raw_targeted.get("artifact_id") != content_artifact_id(
        raw_targeted | {"artifact_id": None}
    ):
        raise StepDispatchError("targeted search plan identity is invalid")
    raw_attempt = raw_targeted.get("attempt")
    if (raw_attempt is None) != (not plan.requests):
        raise StepDispatchError("targeted search selection differs from retrieval plan")
    if not isinstance(raw_attempt, dict):
        return
    if raw_attempt.get("artifact_id") != content_artifact_id(
        raw_attempt | {"artifact_id": None}
    ):
        raise StepDispatchError("targeted search attempt identity is invalid")
    if len(plan.requests) != 1 or (
        plan.requests[0].target_artifact_id
        != raw_attempt.get("requirement_artifact_id")
    ):
        raise StepDispatchError("retrieval plan targets another answer requirement")
    query_text = raw_attempt.get("query_text")
    if not isinstance(query_text, str) or not plan.requests[0].query_text.startswith(
        query_text
    ):
        raise StepDispatchError("retrieval query differs from targeted search")


def _counterevidence_history(
    subject: Mapping[str, object],
    plan: CounterevidencePlan,
    run: CounterevidenceSearchRun | None,
) -> tuple[tuple[CounterevidencePlan, ...], tuple[CounterevidenceSearchRun, ...]]:
    raw_targeted_plans = subject.get("targeted_search_plans")
    raw_counter_plans = subject.get("counterevidence_plans")
    raw_counter_runs = subject.get("counterevidence_runs")
    raw_observations = subject.get("targeted_search_observations")
    if (
        not isinstance(raw_targeted_plans, list)
        or not isinstance(raw_counter_plans, list)
        or not isinstance(raw_counter_runs, list)
        or not isinstance(raw_observations, list)
        or len(raw_targeted_plans) != len(raw_counter_plans)
        or len(raw_counter_runs) != len(raw_observations)
    ):
        raise StepDispatchError("targeted search history is invalid")
    try:
        counter_plans = tuple(
            CounterevidencePlan.model_validate(item) for item in raw_counter_plans
        )
        counter_runs = tuple(
            CounterevidenceSearchRun.model_validate(item) for item in raw_counter_runs
        )
    except ValidationError as error:
        raise StepDispatchError("counterevidence history is invalid") from error
    if not counter_plans or counter_plans[-1] != plan:
        raise StepDispatchError("terminal counterevidence plan differs from history")
    if counter_runs and (run is None or counter_runs[-1] != run):
        raise StepDispatchError("terminal counterevidence run differs from history")
    attempt_ids: list[object] = []
    equivalence_ids: list[object] = []
    for targeted, counter_plan in zip(raw_targeted_plans, counter_plans, strict=True):
        if not isinstance(targeted, dict):
            raise StepDispatchError("targeted search history entry is invalid")
        if targeted.get("artifact_id") != content_artifact_id(
            targeted | {"artifact_id": None}
        ):
            raise StepDispatchError("targeted search history identity is invalid")
        attempt = targeted.get("attempt")
        if (attempt is None) != (not counter_plan.requests):
            raise StepDispatchError("targeted and counterevidence histories differ")
        if isinstance(attempt, dict):
            attempt_ids.append(attempt.get("artifact_id"))
            equivalence_ids.append(attempt.get("query_equivalence_sha256"))
    if len(attempt_ids) != len(set(attempt_ids)) or len(equivalence_ids) != len(
        set(equivalence_ids)
    ):
        raise StepDispatchError("targeted search history repeats an equivalent attempt")
    observed_attempt_ids: list[object] = []
    for observation in raw_observations:
        if not isinstance(observation, dict) or observation.get(
            "artifact_id"
        ) != content_artifact_id(observation | {"artifact_id": None}):
            raise StepDispatchError("targeted search observation identity is invalid")
        observed_attempt_ids.append(observation.get("attempt_artifact_id"))
    if observed_attempt_ids != attempt_ids[: len(observed_attempt_ids)]:
        raise StepDispatchError("targeted search observations refer to other attempts")
    return counter_plans, counter_runs


def _research_requirements(
    subject: Mapping[str, object], records: _ResearchTraceRecords
) -> tuple[dict[str, object], ...]:
    if records.requirements.graph_artifact_id != subject.get("claim_graph_artifact_id"):
        raise StepDispatchError("answer requirement plan refers to another graph")
    raw_requirements = records.raw_state.get("requirements")
    if not isinstance(raw_requirements, list) or any(
        not isinstance(item, dict) for item in raw_requirements
    ):
        raise StepDispatchError("research state requirements are invalid")
    source_requirement_ids = tuple(
        item.get("source_requirement_artifact_id") for item in raw_requirements
    )
    expected_ids = tuple(item.artifact_id for item in records.requirements.requirements)
    if (
        records.raw_state.get("question") != records.requirements.question
        or source_requirement_ids != expected_ids
    ):
        raise StepDispatchError("research state differs from its answer requirements")
    return tuple(raw_requirements)


def _tool_decision_index(
    records: _ResearchTraceRecords,
) -> dict[str, ToolPolicyDecision]:
    allowed_calls: dict[str, int] = {}
    decisions: dict[str, ToolPolicyDecision] = {}
    for sequence, decision in enumerate(records.tool_decisions):
        expected = records.tool_policy.decide(
            decision.invocation,
            sequence=sequence,
            prior_allowed_calls=allowed_calls.get(decision.invocation.tool, 0),
        )
        if decision != expected:
            raise StepDispatchError("research tool policy decision is invalid")
        decisions[decision.artifact_id] = decision
        if decision.action is ToolPolicyAction.ALLOW:
            allowed_calls[decision.invocation.tool] = (
                allowed_calls.get(decision.invocation.tool, 0) + 1
            )
    if len(decisions) != len(records.tool_decisions):
        raise StepDispatchError("research tool decisions repeat identities")
    return decisions


def _tool_record_index(
    records: _ResearchTraceRecords,
    descriptors: Mapping[str, ResearchToolDescriptor],
    decisions: Mapping[str, ToolPolicyDecision],
) -> dict[str, ToolExecutionRecord]:
    executions: dict[str, ToolExecutionRecord] = {}
    for sequence, record in enumerate(records.tool_records):
        decision = decisions.get(record.policy_decision_artifact_id)
        descriptor = descriptors.get(record.descriptor_artifact_id)
        if (
            record.sequence != sequence
            or decision is None
            or decision.action is not ToolPolicyAction.ALLOW
            or descriptor is None
            or record.request_sha256 != decision.invocation.request_sha256
            or descriptor.tool.value != decision.invocation.tool
        ):
            raise StepDispatchError("research tool execution lineage is invalid")
        executions[record.artifact_id] = record
    if len(executions) != len(records.tool_records):
        raise StepDispatchError("research tool executions repeat identities")
    return executions


def _verify_causal_tool_budget_lineage(
    subject: Mapping[str, object], records: _ResearchTraceRecords
) -> None:
    trace = ResearchCausalTrace.create(records.events)
    if records.raw_trace != {
        "artifact_id": trace.artifact_id,
        "event_artifact_ids": list(trace.event_artifact_ids),
        "head_artifact_id": trace.head_artifact_id,
    }:
        raise StepDispatchError("research causal trace identity is invalid")
    if subject.get("budget_policy_artifact_id") != records.budget_policy.artifact_id:
        raise StepDispatchError("research budget policy binding is invalid")
    if subject.get("tool_policy_artifact_id") != records.tool_policy.artifact_id:
        raise StepDispatchError("research tool policy identity is invalid")
    descriptors = {item.artifact_id: item for item in records.tool_descriptors}
    if len(descriptors) != len(records.tool_descriptors) or not descriptors:
        raise StepDispatchError("research tool descriptor inventory is invalid")
    decisions = _tool_decision_index(records)
    executions = _tool_record_index(records, descriptors, decisions)
    if _budget_dimensions(subject.get("budget_usage"), "budget_usage") != (
        records.budget.global_usage
    ):
        raise StepDispatchError("research budget usage is not reproducible")
    document_ids = _strings(
        subject.get("counterevidence_document_artifact_ids"),
        "counterevidence_document_artifact_ids",
    )
    if records.budget.global_usage.documents != len(document_ids):
        raise StepDispatchError("research document budget differs from search history")
    referenced_budget_ids = {
        artifact_id
        for event in records.events
        for artifact_id in event.budget_decision_artifact_ids
    }
    if {item.artifact_id for item in records.budget_decisions} != referenced_budget_ids:
        raise StepDispatchError("research causal trace omits budget decisions")
    referenced_decisions = {
        artifact_id
        for event in records.events
        for artifact_id in event.tool_decision_artifact_ids
    }
    referenced_executions = {
        artifact_id
        for event in records.events
        for artifact_id in event.observation_artifact_ids
        if artifact_id in executions
    }
    if set(decisions) != referenced_decisions:
        raise StepDispatchError("research causal trace omits tool decisions")
    if set(executions) != referenced_executions:
        raise StepDispatchError("research causal trace omits tool executions")
    if records.budget.global_usage.tool_calls != len(records.tool_decisions):
        raise StepDispatchError("research tool-call budget differs from decisions")


def _verify_budget_termination(records: _ResearchTraceRecords) -> None:
    convergence = records.convergence
    convergence_dimensions = (
        tuple(
            {
                "iteration_limit": "iterations",
                "tool_limit": "tool_calls",
                "token_limit": "tokens",
                "time_limit": "elapsed_ms",
            }[item.value]
            for item in convergence.reasons
            if item.value
            in {"iteration_limit", "tool_limit", "token_limit", "time_limit"}
        )
        if isinstance(convergence, ConvergenceDecision)
        and convergence.outcome.value == "budget_exhausted"
        else ()
    )
    outcome = records.research_outcome
    budget = records.budget
    if budget.exhausted_dimensions:
        if outcome.exhausted_budget_dimensions != budget.exhausted_dimensions:
            raise StepDispatchError("research budget exhaustion differs from ledger")
    elif outcome.kind is InstalledResearchTerminalKind.INCOMPLETE_BUDGET:
        raw_search_budget = _object(records.raw_state["search_budget"], "search_budget")
        remaining_work = records.remaining_work
        search_budget_exhausted = (
            remaining_work.pending
            and _integer(raw_search_budget["used"], "search_budget.used")
            >= _integer(raw_search_budget["limit"], "search_budget.limit")
            and bool(
                remaining_work.unsatisfied_requirement_artifact_ids
                or remaining_work.unsearched_important_claim_artifact_ids
            )
        )
        expected_dimensions = tuple(
            dict.fromkeys(
                convergence_dimensions
                + (("retrievals",) if search_budget_exhausted else ())
            )
        )
        if (
            not expected_dimensions
            or outcome.exhausted_budget_dimensions != expected_dimensions
        ):
            raise StepDispatchError("research search-budget exhaustion is invalid")
    if not convergence.stop:
        raise StepDispatchError("research trace did not reach a terminal decision")


def _candidate_lineage(
    subject: Mapping[str, object],
    raw_state: Mapping[str, object],
    counter_runs: tuple[CounterevidenceSearchRun, ...],
) -> tuple[
    tuple[str, ...],
    tuple[ResearchCandidateClassification, ...],
    ResearchAnswerRevision | None,
]:
    candidate_ids = tuple(
        artifact_id
        for history_run in counter_runs
        for record in history_run.records
        for artifact_id in record.candidate_evidence_artifact_ids
    )
    if _strings(subject.get("opposition_candidates"), "opposition_candidates") != (
        candidate_ids
    ):
        raise StepDispatchError("research opposition candidates do not match search")
    if _strings(subject.get("research_candidates"), "research_candidates") != (
        candidate_ids
    ):
        raise StepDispatchError("research candidates do not match search")
    raw_adjudications = subject.get("candidate_adjudications")
    raw_classifications = subject.get("candidate_classifications")
    if not isinstance(raw_adjudications, list) or not isinstance(
        raw_classifications, list
    ):
        raise StepDispatchError("research candidate adjudication is missing")
    try:
        adjudications = tuple(
            CandidateAdjudicationReport.model_validate(item)
            for item in raw_adjudications
        )
        classifications = tuple(
            ResearchCandidateClassification.model_validate(item)
            for item in raw_classifications
        )
    except ValidationError as error:
        raise StepDispatchError("research candidate adjudication is invalid") from error
    report_classifications = tuple(
        classification
        for report in adjudications
        for classification in report.classifications
    )
    if report_classifications != classifications:
        raise StepDispatchError("candidate classifications differ from reports")
    reported_candidate_ids = {
        artifact_id
        for report in adjudications
        for artifact_id in report.input_evidence_artifact_ids
    }
    if reported_candidate_ids != set(candidate_ids):
        raise StepDispatchError("candidate adjudication coverage is incomplete")
    revision = _answer_revision(subject, classifications, candidate_ids)
    material_unresolved = {
        classification.evidence_artifact_id
        for classification in classifications
        if classification.material
        and classification.relation.value in {"ambiguous", "unclassified"}
    }
    if raw_state.get("terminal_status") == "completed" and material_unresolved:
        raise StepDispatchError("completed research retains unresolved evidence")
    return candidate_ids, classifications, revision


def _answer_revision(
    subject: Mapping[str, object],
    classifications: tuple[ResearchCandidateClassification, ...],
    candidate_ids: tuple[str, ...],
) -> ResearchAnswerRevision | None:
    raw_revision = subject.get("answer_revision")
    if raw_revision is None:
        if subject.get("answer_revision_artifact_id") is not None:
            raise StepDispatchError("research answer revision record is missing")
        return None
    try:
        revision = ResearchAnswerRevision.model_validate(raw_revision)
    except ValidationError as error:
        raise StepDispatchError("research answer revision is invalid") from error
    if (
        subject.get("answer_revision_artifact_id") != revision.artifact_id
        or subject.get("answer") != revision.after_answer
        or revision.prior_claim_graph_artifact_id
        != subject.get("claim_graph_artifact_id")
        or revision.classification_artifact_ids
        != tuple(item.artifact_id for item in classifications)
        or set(revision.candidate_evidence_artifact_ids) != set(candidate_ids)
    ):
        raise StepDispatchError("research answer revision lineage is invalid")
    material_opposition_ids = {
        item.artifact_id
        for item in classifications
        if item.material and item.relation.value in {"opposing", "limiting"}
    }
    if (
        material_opposition_ids <= set(revision.resolved_classification_artifact_ids)
        and material_opposition_ids
        and revision.before_answer == revision.after_answer
    ):
        raise StepDispatchError("material counterevidence did not revise the answer")
    return revision


def _verify_remaining_work(
    records: _ResearchTraceRecords,
    raw_requirements: tuple[dict[str, object], ...],
    classifications: tuple[ResearchCandidateClassification, ...],
    candidate_ids: tuple[str, ...],
    counter_runs: tuple[CounterevidenceSearchRun, ...],
) -> tuple[set[str], tuple[str, ...]]:
    expected_unsatisfied = tuple(
        str(item["artifact_id"])
        for item in raw_requirements
        if item.get("material") is True and item.get("status") != "satisfied"
    )
    raw_gaps = records.raw_state.get("gaps")
    if not isinstance(raw_gaps, list) or any(
        not isinstance(item, dict) for item in raw_gaps
    ):
        raise StepDispatchError("research state gaps are invalid")
    expected_gaps = tuple(
        str(item["artifact_id"]) for item in raw_gaps if item.get("blocking") is True
    )
    if records.budget.exhausted_dimensions and not expected_gaps:
        expected_gaps = (records.budget_decisions[-1].artifact_id,)
    classified_candidate_ids = {
        classification.evidence_artifact_id for classification in classifications
    }
    expected_evidence = tuple(
        dict.fromkeys(
            tuple(
                classification.evidence_artifact_id
                for classification in classifications
                if classification.material
                and classification.relation.value in {"ambiguous", "unclassified"}
            )
            + tuple(
                artifact_id
                for artifact_id in candidate_ids
                if artifact_id not in classified_candidate_ids
            )
        )
    )
    expected_unsearched = tuple(
        dict.fromkeys(
            artifact_id
            for history_run in counter_runs
            for artifact_id in history_run.unsearched_important_claim_artifact_ids
        )
    )
    remaining = records.remaining_work
    if (
        remaining.unsatisfied_requirement_artifact_ids != expected_unsatisfied
        or remaining.unresolved_evidence_artifact_ids != expected_evidence
        or remaining.unresolved_gap_artifact_ids != expected_gaps
        or remaining.unsearched_important_claim_artifact_ids != expected_unsearched
    ):
        raise StepDispatchError("research terminal remaining work is incomplete")
    return classified_candidate_ids, expected_unsearched


def _marginal_evidence_values(
    counter_runs: tuple[CounterevidenceSearchRun, ...],
) -> tuple[float, ...]:
    seen_candidates: set[str] = set()
    values: list[float] = []
    for history_run in counter_runs:
        run_candidate_ids = tuple(
            dict.fromkeys(
                artifact_id
                for record in history_run.records
                for artifact_id in record.candidate_evidence_artifact_ids
            )
        )
        new_candidate_ids = tuple(
            item for item in run_candidate_ids if item not in seen_candidates
        )
        values.append(
            0.0
            if not run_candidate_ids
            else len(new_candidate_ids) / len(run_candidate_ids)
        )
        seen_candidates.update(run_candidate_ids)
    return tuple(values)


def _verify_semantic_convergence(
    subject: Mapping[str, object],
    records: _ResearchTraceRecords,
    raw_requirements: tuple[dict[str, object], ...],
    classifications: tuple[ResearchCandidateClassification, ...],
    candidate_ids: tuple[str, ...],
    classified_candidate_ids: set[str],
    expected_unsearched: tuple[str, ...],
    counter_runs: tuple[CounterevidenceSearchRun, ...],
    revision: ResearchAnswerRevision | None,
) -> None:
    convergence = records.convergence
    if not isinstance(convergence, ConvergenceDecision):
        return
    evidence = convergence.evidence
    if evidence is None:
        raise StepDispatchError("semantic convergence evidence is missing")
    material_requirements = tuple(
        item for item in raw_requirements if item.get("material") is True
    )
    satisfied_requirement_ids = tuple(
        str(item.get("source_requirement_artifact_id") or item["artifact_id"])
        for item in material_requirements
        if item.get("status") == "satisfied"
    )
    remaining_requirement_ids = tuple(
        str(item.get("source_requirement_artifact_id") or item["artifact_id"])
        for item in material_requirements
        if item.get("status") != "satisfied"
    )
    unresolved_classification_ids = tuple(
        dict.fromkeys(
            tuple(
                item.artifact_id
                for item in classifications
                if item.material
                and item.relation.value in {"ambiguous", "unclassified"}
            )
            + tuple(
                artifact_id
                for artifact_id in candidate_ids
                if artifact_id not in classified_candidate_ids
            )
        )
    )
    blocking_ids = tuple(
        dict.fromkeys(
            remaining_requirement_ids
            + unresolved_classification_ids
            + expected_unsearched
        )
    )
    expected_answer_status = (
        revision.revised_answer.outcome.value
        if revision is not None
        else subject.get("grounding_admission_outcome")
    )
    expected_graph_id = (
        str(subject["claim_graph_artifact_id"])
        if revision is None
        else revision.revised_answer.artifact_id
    )
    if (
        evidence.current_graph_artifact_id != expected_graph_id
        or evidence.material_requirement_count != len(material_requirements)
        or evidence.satisfied_requirement_artifact_ids != satisfied_requirement_ids
        or evidence.remaining_requirement_artifact_ids != remaining_requirement_ids
        or evidence.material_candidate_count != len(set(candidate_ids))
        or evidence.classified_candidate_count
        != len(set(candidate_ids) & classified_candidate_ids)
        or evidence.unresolved_classification_artifact_ids
        != unresolved_classification_ids
        or evidence.blocking_gap_artifact_ids != blocking_ids
        or evidence.unsearched_important_claim_artifact_ids != expected_unsearched
        or evidence.answer_verification_status.value != expected_answer_status
        or evidence.answer_revision_artifact_id
        != (None if revision is None else revision.artifact_id)
        or evidence.marginal_evidence_values != _marginal_evidence_values(counter_runs)
    ):
        raise StepDispatchError("semantic convergence evidence differs from trace")
    if revision is not None and evidence.material_conflict_count != len(
        revision.revised_answer.contextualized.conflicts
    ):
        raise StepDispatchError("semantic convergence conflict count differs")
    if (
        records.research_outcome.kind is InstalledResearchTerminalKind.CONVERGED
        and not evidence.answerable
    ):
        raise StepDispatchError("research completion differs from convergence evidence")


def _verify_research_trace(subject: Mapping[str, object]) -> tuple[str, ...]:
    records = _research_trace_records(subject)
    plan = records.plan
    run = records.run
    convergence = records.convergence
    raw_state = records.raw_state
    _verify_research_terminal(subject, records)
    _verify_targeted_search(subject, plan)
    _, counter_runs = _counterevidence_history(subject, plan, run)
    raw_requirements = _research_requirements(subject, records)
    _verify_causal_tool_budget_lineage(subject, records)
    _verify_budget_termination(records)
    candidate_ids, classifications, revision = _candidate_lineage(
        subject, raw_state, counter_runs
    )
    classified_candidate_ids, expected_unsearched = _verify_remaining_work(
        records,
        raw_requirements,
        classifications,
        candidate_ids,
        counter_runs,
    )
    _verify_semantic_convergence(
        subject,
        records,
        raw_requirements,
        classifications,
        candidate_ids,
        classified_candidate_ids,
        expected_unsearched,
        counter_runs,
        revision,
    )
    checks = (
        "answer-requirement-plan-identity",
        "targeted-search-plan-identity",
        "targeted-search-history-lineage",
        "counterevidence-plan-identity",
        "counterevidence-search-lineage",
        "semantic-candidate-adjudication",
        "verified-answer-revision",
        "bounded-convergence-decision",
        "transactional-budget-ledger",
        "default-deny-tool-policy",
        "tool-decision-execution-lineage",
        "typed-terminal-outcome",
        "causal-event-chain",
    )
    return checks + (
        ("semantic-convergence-evidence",)
        if isinstance(convergence, ConvergenceDecision)
        else ()
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
            checks = _verify_claim_graph(
                subject,
                subject_dependency_ids=frozenset(
                    str(item) for item in subject_artifact.descriptor.dependencies
                ),
            )
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
