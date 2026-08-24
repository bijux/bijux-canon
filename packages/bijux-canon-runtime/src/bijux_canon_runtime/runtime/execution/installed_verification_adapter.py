# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Installed verification of grounded answers and research traces."""

from __future__ import annotations

from collections.abc import Mapping

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
)
from bijux_canon_reason.grounding import (
    AtomicClaimNormalizer,
    CitationSourceDescriptor,
    CitationPresentation,
    CitationPresentationService,
    CitationVerificationReport,
    ClaimCitationLinker,
    ClaimCitationSet,
    CredentialFreeSynthesis,
    DeterministicCitationVerifier,
    EvidencePacket,
    GroundingAdmissionDecision,
    GroundingAdmissionService,
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
            global_usage=_budget_dimensions(
                raw["global_usage"], "budget global_usage"
            ),
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
            contextualized = NuancedGroundingRepresentation.model_validate(
                subject["contextualized"]
            )
            expected_answer = render_grounded_answer(
                synthesis=synthesis,
                claims=claims,
                citations=citations,
                admission=admission,
                citation_presentation=citation_presentation,
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
            )
        except (KeyError, TypeError, ValidationError) as error:
            raise StepDispatchError("local grounded answer is invalid") from error
        if (
            GroundingAdmissionService().decide(
                claim_set=claims,
                citation_set=citations,
                verification_report=verification,
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


def _verify_research_trace(subject: Mapping[str, object]) -> tuple[str, ...]:
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
        convergence = (
            InstalledResearchConvergence(
                artifact_id=str(
                    _object(subject["termination"], "termination")["artifact_id"]
                ),
                outcome=str(
                    _object(subject["termination"], "termination")["outcome"]
                ),
                stop=_boolean(
                    _object(subject["termination"], "termination")["stop"],
                    "termination.stop",
                ),
                record=_object(subject["termination"], "termination"),
            )
            if subject.get("status") == "cancelled"
            else ConvergenceDecision.model_validate(subject["termination"])
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
    except (KeyError, TypeError, ValueError, ValidationError) as error:
        raise StepDispatchError("research trace records are invalid") from error
    if run is not None and run.plan_artifact_id != plan.artifact_id:
        raise StepDispatchError("counterevidence run refers to another plan")
    convergence_outcome = (
        convergence.outcome
        if isinstance(convergence, InstalledResearchConvergence)
        else convergence.outcome.value
    )
    if (
        research_outcome.convergence_artifact_id != convergence.artifact_id
        or research_outcome.convergence_outcome != convergence_outcome
        or subject.get("status") != research_outcome.kind.value
        or subject.get("convergence_status") != convergence_outcome
    ):
        raise StepDispatchError("research terminal outcome differs from convergence")
    if cancellation_signal is not None:
        if (
            research_outcome.cancellation_artifact_id
            != cancellation_signal.artifact_id
        ):
            raise StepDispatchError("research cancellation identity is invalid")
    elif research_outcome.cancellation_artifact_id is not None:
        raise StepDispatchError("research cancellation signal is missing")
    raw_targeted = subject.get("targeted_search_plan")
    if not isinstance(raw_targeted, dict):
        raise StepDispatchError("targeted search plan is missing or invalid")
    targeted_id = raw_targeted.get("artifact_id")
    if targeted_id != content_artifact_id(raw_targeted | {"artifact_id": None}):
        raise StepDispatchError("targeted search plan identity is invalid")
    raw_attempt = raw_targeted.get("attempt")
    if (raw_attempt is None) != (not plan.requests):
        raise StepDispatchError("targeted search selection differs from retrieval plan")
    if isinstance(raw_attempt, dict):
        attempt_id = raw_attempt.get("artifact_id")
        if attempt_id != content_artifact_id(raw_attempt | {"artifact_id": None}):
            raise StepDispatchError("targeted search attempt identity is invalid")
        if len(plan.requests) != 1 or (
            plan.requests[0].target_artifact_id
            != raw_attempt.get("requirement_artifact_id")
        ):
            raise StepDispatchError("retrieval plan targets another answer requirement")
        query_text = raw_attempt.get("query_text")
        if not isinstance(query_text, str) or not plan.requests[
            0
        ].query_text.startswith(query_text):
            raise StepDispatchError("retrieval query differs from targeted search")
    raw_targeted_plans = subject.get("targeted_search_plans")
    raw_counter_plans = subject.get("counterevidence_plans")
    raw_counter_runs = subject.get("counterevidence_runs")
    raw_search_observations = subject.get("targeted_search_observations")
    if (
        not isinstance(raw_targeted_plans, list)
        or not isinstance(raw_counter_plans, list)
        or not isinstance(raw_counter_runs, list)
        or not isinstance(raw_search_observations, list)
        or len(raw_targeted_plans) != len(raw_counter_plans)
        or len(raw_counter_runs) != len(raw_search_observations)
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
    for observation in raw_search_observations:
        if not isinstance(observation, dict) or observation.get(
            "artifact_id"
        ) != content_artifact_id(observation | {"artifact_id": None}):
            raise StepDispatchError("targeted search observation identity is invalid")
        observed_attempt_ids.append(observation.get("attempt_artifact_id"))
    if observed_attempt_ids != attempt_ids[: len(observed_attempt_ids)]:
        raise StepDispatchError("targeted search observations refer to other attempts")
    if requirements.graph_artifact_id != subject.get("claim_graph_artifact_id"):
        raise StepDispatchError("answer requirement plan refers to another graph")
    raw_requirements = raw_state.get("requirements")
    if not isinstance(raw_requirements, list) or any(
        not isinstance(item, dict) for item in raw_requirements
    ):
        raise StepDispatchError("research state requirements are invalid")
    source_requirement_ids = tuple(
        item.get("source_requirement_artifact_id")
        for item in raw_requirements
        if isinstance(item, dict)
    )
    if raw_state.get("question") != requirements.question or (
        source_requirement_ids
        != tuple(item.artifact_id for item in requirements.requirements)
    ):
        raise StepDispatchError("research state differs from its answer requirements")
    trace = ResearchCausalTrace.create(events)
    if raw_trace != {
        "artifact_id": trace.artifact_id,
        "event_artifact_ids": list(trace.event_artifact_ids),
        "head_artifact_id": trace.head_artifact_id,
    }:
        raise StepDispatchError("research causal trace identity is invalid")
    if subject.get("budget_policy_artifact_id") != budget_policy.artifact_id:
        raise StepDispatchError("research budget policy binding is invalid")
    if _budget_dimensions(subject.get("budget_usage"), "budget_usage") != (
        budget.global_usage
    ):
        raise StepDispatchError("research budget usage is not reproducible")
    document_ids = _strings(
        subject.get("counterevidence_document_artifact_ids"),
        "counterevidence_document_artifact_ids",
    )
    if budget.global_usage.documents != len(document_ids):
        raise StepDispatchError("research document budget differs from search history")
    decision_ids = {item.artifact_id for item in budget_decisions}
    referenced_budget_ids = {
        artifact_id
        for event in events
        for artifact_id in event.budget_decision_artifact_ids
    }
    if decision_ids != referenced_budget_ids:
        raise StepDispatchError("research causal trace omits budget decisions")
    if budget.exhausted_dimensions:
        if (
            research_outcome.exhausted_budget_dimensions
            != budget.exhausted_dimensions
        ):
            raise StepDispatchError("research budget exhaustion differs from ledger")
    elif research_outcome.kind is InstalledResearchTerminalKind.INCOMPLETE_BUDGET:
        if (
            research_outcome.exhausted_budget_dimensions != ("retrievals",)
            or budget.global_usage.retrievals
            != budget_policy.global_limits.retrievals
        ):
            raise StepDispatchError("research search-budget exhaustion is invalid")
    if not convergence.stop:
        raise StepDispatchError("research trace did not reach a terminal decision")
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
    material_unresolved = {
        classification.evidence_artifact_id
        for classification in classifications
        if classification.material
        and classification.relation.value in {"ambiguous", "unclassified"}
    }
    if raw_state.get("terminal_status") == "completed" and material_unresolved:
        raise StepDispatchError("completed research retains unresolved evidence")
    expected_unsatisfied_requirements = tuple(
        str(item["artifact_id"])
        for item in raw_requirements
        if item.get("material") is True and item.get("status") != "satisfied"
    )
    raw_gaps = raw_state.get("gaps")
    if not isinstance(raw_gaps, list) or any(
        not isinstance(item, dict) for item in raw_gaps
    ):
        raise StepDispatchError("research state gaps are invalid")
    expected_unresolved_gaps = tuple(
        str(item["artifact_id"]) for item in raw_gaps if item.get("blocking") is True
    )
    if budget.exhausted_dimensions and not expected_unresolved_gaps:
        expected_unresolved_gaps = (budget_decisions[-1].artifact_id,)
    classified_candidate_ids = {
        classification.evidence_artifact_id for classification in classifications
    }
    expected_unresolved_evidence = tuple(
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
    if (
        remaining_work.unsatisfied_requirement_artifact_ids
        != expected_unsatisfied_requirements
        or remaining_work.unresolved_evidence_artifact_ids
        != expected_unresolved_evidence
        or remaining_work.unresolved_gap_artifact_ids != expected_unresolved_gaps
        or remaining_work.unsearched_important_claim_artifact_ids != expected_unsearched
    ):
        raise StepDispatchError("research terminal remaining work is incomplete")
    return (
        "answer-requirement-plan-identity",
        "targeted-search-plan-identity",
        "targeted-search-history-lineage",
        "counterevidence-plan-identity",
        "counterevidence-search-lineage",
        "semantic-candidate-adjudication",
        "bounded-convergence-decision",
        "transactional-budget-ledger",
        "typed-terminal-outcome",
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
