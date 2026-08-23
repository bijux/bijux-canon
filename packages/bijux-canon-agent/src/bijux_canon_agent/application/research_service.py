"""Agent-owned orchestration for installed counterevidence research."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
from typing import Protocol, runtime_checkable

from bijux_canon_agent.contracts.causal_trace import (
    CausalDecisionEvent,
    ResearchCausalTrace,
)
from bijux_canon_agent.application.research_workflow.observed_state import (
    InstalledEvidenceRelation,
    InstalledResearchRequirement,
    ObservedEvidenceRelationKind,
    ObservedResearchDecision,
    ObservedResearchGap,
    ObservedResearchGapKind,
    ObservedResearchState,
    ObservedResearchStateMachine,
)
from bijux_canon_agent.application.research_workflow.targeted_search import (
    TargetedSearchPlan,
    TargetedSearchPlanningService,
    TargetedSearchPolicy,
)


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _artifact_id(value: object) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value)).hexdigest()


def _require_artifact_id(value: str, field: str) -> None:
    if not value.startswith("sha256:") or len(value) != 71:
        raise ValueError(f"{field} must be a SHA-256 artifact ID")


@dataclass(frozen=True, slots=True)
class InstalledResearchClaim:
    """One atomic claim selected for skeptical research."""

    artifact_id: str
    statement: str
    importance: int
    known_evidence_artifact_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_artifact_id(self.artifact_id, "claim artifact_id")
        if not self.statement.strip() or self.importance < 0:
            raise ValueError("research claim statement and importance are invalid")
        for artifact_id in self.known_evidence_artifact_ids:
            _require_artifact_id(artifact_id, "known evidence artifact_id")


@dataclass(frozen=True, slots=True)
class InstalledResearchRequest:
    """Complete Runtime-neutral input to one installed research cycle."""

    claim_graph_artifact_id: str
    scope_artifact_id: str
    claims: tuple[InstalledResearchClaim, ...]
    verified_claim_count: int
    counterevidence_policy_artifact_id: str
    convergence_policy_artifact_id: str
    question: str
    requirements: tuple[InstalledResearchRequirement, ...]
    evidence_relations: tuple[InstalledEvidenceRelation, ...]
    max_searches: int
    requirement_plan_artifact_id: str
    requirement_plan_record: Mapping[str, object]
    requirement_plan_outcome: str

    def __post_init__(self) -> None:
        for value, field in (
            (self.claim_graph_artifact_id, "claim graph artifact_id"),
            (self.scope_artifact_id, "scope artifact_id"),
            (self.counterevidence_policy_artifact_id, "counterevidence policy"),
            (self.convergence_policy_artifact_id, "convergence policy"),
            (self.requirement_plan_artifact_id, "requirement plan artifact_id"),
        ):
            _require_artifact_id(value, field)
        if self.verified_claim_count < 0:
            raise ValueError("verified claim count must not be negative")
        if not self.question.strip():
            raise ValueError("research question must not be empty")
        if self.max_searches < 0:
            raise ValueError("maximum searches must not be negative")
        claim_ids = {claim.artifact_id for claim in self.claims}
        finding_claim_ids = tuple(
            item.claim_artifact_id
            for item in self.requirements
            if item.kind == "finding" and item.claim_artifact_id is not None
        )
        if set(finding_claim_ids) != claim_ids or len(finding_claim_ids) != len(
            set(finding_claim_ids)
        ):
            raise ValueError(
                "finding requirements must cover every claim exactly once"
            )
        if self.verified_claim_count != sum(
            item.satisfied for item in self.requirements if item.kind == "finding"
        ):
            raise ValueError("verified claim count must match satisfied requirements")
        if any(
            claim_id not in claim_ids
            for item in self.requirements
            for claim_id in item.target_claim_artifact_ids
        ):
            raise ValueError("research requirement references an unknown claim")
        if any(
            item.claim_artifact_id not in claim_ids for item in self.evidence_relations
        ):
            raise ValueError("evidence relation references an unknown claim")
        if not isinstance(self.requirement_plan_record, Mapping):
            raise TypeError("requirement plan record must be a mapping")
        if not self.requirement_plan_outcome:
            raise ValueError("requirement plan outcome must not be empty")
        if self.requirement_plan_record.get("artifact_id") not in {
            None,
            self.requirement_plan_artifact_id,
        } or self.requirement_plan_record.get("outcome") not in {
            None,
            self.requirement_plan_outcome,
        }:
            raise ValueError("requirement plan summary differs from its identity")


@dataclass(frozen=True, slots=True)
class InstalledResearchPlan:
    """Counterevidence plan returned by the injected reasoning port."""

    artifact_id: str
    request_artifact_ids: tuple[str, ...]
    record: Mapping[str, object]
    targeted_search_plan: TargetedSearchPlan | None = None

    def __post_init__(self) -> None:
        _require_artifact_id(self.artifact_id, "research plan artifact_id")
        for artifact_id in self.request_artifact_ids:
            _require_artifact_id(artifact_id, "research request artifact_id")
        if not isinstance(self.record, Mapping):
            raise TypeError("research plan record must be a mapping")
        if self.targeted_search_plan is not None:
            attempt = self.targeted_search_plan.attempt
            if (attempt is None) != (not self.request_artifact_ids):
                raise ValueError(
                    "targeted search selection must match executable requests"
                )


@dataclass(frozen=True, slots=True)
class InstalledResearchSearchRecord:
    """One material result of a skeptical retrieval request."""

    claim_artifact_id: str
    outcome: str
    candidate_evidence_artifact_ids: tuple[str, ...]
    negative_search_statement: str | None
    record: Mapping[str, object]
    requirement_artifact_id: str | None = None
    target_claim_artifact_ids: tuple[str, ...] | None = None
    attempt_artifact_id: str | None = None

    def __post_init__(self) -> None:
        _require_artifact_id(self.claim_artifact_id, "searched claim artifact_id")
        if not self.outcome:
            raise ValueError("research search outcome must not be empty")
        for artifact_id in self.candidate_evidence_artifact_ids:
            _require_artifact_id(artifact_id, "candidate evidence artifact_id")
        for artifact_id in (
            (() if self.requirement_artifact_id is None else (self.requirement_artifact_id,))
            + (() if self.target_claim_artifact_ids is None else self.target_claim_artifact_ids)
            + (() if self.attempt_artifact_id is None else (self.attempt_artifact_id,))
        ):
            _require_artifact_id(artifact_id, "targeted search record reference")
        if not isinstance(self.record, Mapping):
            raise TypeError("research search record must be a mapping")

    @property
    def effective_target_claim_artifact_ids(self) -> tuple[str, ...]:
        """Return explicit claim targets or the compatibility claim target."""
        return (
            (self.claim_artifact_id,)
            if self.target_claim_artifact_ids is None
            else self.target_claim_artifact_ids
        )


@dataclass(frozen=True, slots=True)
class InstalledResearchSearch:
    """Complete search output plus persisted Runtime retrieval artifacts."""

    artifact_id: str
    records: tuple[InstalledResearchSearchRecord, ...]
    unsearched_important_claim_artifact_ids: tuple[str, ...]
    retrieval_artifact_ids: tuple[str, ...]
    retrieval_records: tuple[Mapping[str, object], ...]
    record: Mapping[str, object]

    def __post_init__(self) -> None:
        _require_artifact_id(self.artifact_id, "research search artifact_id")
        for artifact_id in self.unsearched_important_claim_artifact_ids:
            _require_artifact_id(artifact_id, "unsearched claim artifact_id")
        for artifact_id in self.retrieval_artifact_ids:
            _require_artifact_id(artifact_id, "retrieval artifact_id")
        if any(not isinstance(item, Mapping) for item in self.retrieval_records):
            raise TypeError("research retrieval records must be mappings")
        if not isinstance(self.record, Mapping):
            raise TypeError("research search output must be a mapping")


@dataclass(frozen=True, slots=True)
class InstalledResearchConvergence:
    """Typed convergence decision returned by the reasoning port."""

    artifact_id: str
    outcome: str
    stop: bool
    record: Mapping[str, object]

    def __post_init__(self) -> None:
        _require_artifact_id(self.artifact_id, "research convergence artifact_id")
        if not self.outcome:
            raise ValueError("research convergence outcome must not be empty")
        if not isinstance(self.record, Mapping):
            raise TypeError("research convergence record must be a mapping")


@runtime_checkable
class InstalledResearchPort(Protocol):
    """Runtime-supplied Reason and retrieval operations used by Agent."""

    def plan(
        self,
        request: InstalledResearchRequest,
        targeted_search_plan: TargetedSearchPlan | None,
    ) -> InstalledResearchPlan: ...

    def search(
        self,
        request: InstalledResearchRequest,
        plan: InstalledResearchPlan,
    ) -> InstalledResearchSearch: ...

    def evaluate(
        self,
        request: InstalledResearchRequest,
        plan: InstalledResearchPlan,
        search: InstalledResearchSearch | None,
    ) -> InstalledResearchConvergence: ...


@dataclass(frozen=True, slots=True)
class InstalledResearchResult:
    """Agent-owned terminal result projected by Runtime into its artifact."""

    plan: InstalledResearchPlan
    search: InstalledResearchSearch | None
    convergence: InstalledResearchConvergence
    opposition_candidate_ids: tuple[str, ...]
    relation_status: str
    insufficiencies: tuple[str, ...]
    state_history: tuple[ObservedResearchState, ...]
    final_state: ObservedResearchState
    tool_failure_artifact_ids: tuple[str, ...]
    causal_events: tuple[CausalDecisionEvent, ...]
    causal_trace: ResearchCausalTrace


class InstalledResearchService:
    """Choose and execute installed research operations through typed ports."""

    def research(
        self,
        request: InstalledResearchRequest,
        port: InstalledResearchPort,
    ) -> InstalledResearchResult:
        """Run only operations justified by the current plan and observations."""
        if not isinstance(request, InstalledResearchRequest):
            raise TypeError("installed research request has the wrong type")
        if not isinstance(port, InstalledResearchPort):
            raise TypeError("installed research port does not implement its contract")
        events: list[CausalDecisionEvent] = []
        state_machine = ObservedResearchStateMachine()
        state = state_machine.initial(
            question=request.question,
            requirements=request.requirements,
            claim_artifact_ids=tuple(claim.artifact_id for claim in request.claims),
            evidence_relations=request.evidence_relations,
            search_budget_limit=request.max_searches,
        )
        state_history = [state]
        policy_ids = (
            request.counterevidence_policy_artifact_id,
            request.convergence_policy_artifact_id,
        )
        targeted_search_plan = (
            None
            if request.max_searches == 0
            else TargetedSearchPlanningService(
                TargetedSearchPolicy(
                    max_attempts=request.max_searches,
                    max_attempts_per_requirement=min(2, request.max_searches),
                )
            ).plan(request.requirements)
        )
        plan = port.plan(request, targeted_search_plan)
        if not isinstance(plan, InstalledResearchPlan):
            raise TypeError("installed research port returned an invalid plan")
        state = self._record_decision(
            events,
            state_machine=state_machine,
            state=state,
            state_history=state_history,
            role="plan",
            operation="plan_counterevidence",
            rationale=(
                "select important atomic claims only where observed evidence needs "
                "justify deliberate skeptical search"
            ),
            observation_ids=(plan.artifact_id,),
            evidence_ids=(),
            policy_ids=policy_ids,
        )
        search: InstalledResearchSearch | None = None
        tool_failure_ids: tuple[str, ...] = ()
        if plan.request_artifact_ids and state.search_budget_used < state.search_budget_limit:
            try:
                search = port.search(request, plan)
                if not isinstance(search, InstalledResearchSearch):
                    raise TypeError("installed research port returned an invalid search")
            except Exception as error:
                failure_id = _artifact_id(
                    {
                        "error_type": type(error).__name__,
                        "operation": "search_counterevidence",
                        "plan_artifact_id": plan.artifact_id,
                    }
                )
                tool_failure_ids = (failure_id,)
                failure_gap = ObservedResearchGap.create(
                    kind=ObservedResearchGapKind.TOOL_FAILURE,
                    subject_artifact_id=failure_id,
                )
                state = self._record_decision(
                    events,
                    state_machine=state_machine,
                    state=state,
                    state_history=state_history,
                    role="researcher",
                    operation="record_search_tool_failure",
                    rationale=(
                        "retain the typed tool failure without treating missing "
                        "results as negative evidence"
                    ),
                    observation_ids=(failure_id,),
                    evidence_ids=(),
                    policy_ids=policy_ids,
                    gaps=state.gaps + (failure_gap,),
                    consume_search=True,
                )
            if search is not None:
                state = self._record_decision(
                    events,
                    state_machine=state_machine,
                    state=state,
                    state_history=state_history,
                    role="researcher",
                    operation="search_counterevidence",
                    rationale=(
                        "execute the planned bounded search because unresolved "
                        "evidence needs remain"
                    ),
                    observation_ids=(search.artifact_id,),
                    evidence_ids=(),
                    policy_ids=policy_ids,
                    consume_search=True,
                )
            candidates = tuple(
                artifact_id
                for record in (() if search is None else search.records)
                for artifact_id in record.candidate_evidence_artifact_ids
            )
            if search is not None:
                state = self._record_search_observation(
                    events=events,
                    state_machine=state_machine,
                    state=state,
                    state_history=state_history,
                    search=search,
                    candidates=candidates,
                    policy_ids=policy_ids,
                )
        else:
            candidates = ()
            role = "verifier" if not state.blocking_gaps else "adjudicator"
            operation = (
                "preserve_sufficient_answer"
                if not state.blocking_gaps
                else "retain_unresolved_requirements"
            )
            state = self._record_decision(
                events,
                state_machine=state_machine,
                state=state,
                state_history=state_history,
                role=role,
                operation=operation,
                rationale=(
                    "the observed requirements are already satisfied, so a second "
                    "search is not needed"
                    if not state.blocking_gaps
                    else "the plan exposed no executable search for blocking gaps"
                ),
                observation_ids=(plan.artifact_id,),
                evidence_ids=(),
                policy_ids=policy_ids,
            )

        relation_status = self._relation_status(state, search, tool_failure_ids)
        convergence = port.evaluate(request, plan, search)
        if not isinstance(convergence, InstalledResearchConvergence):
            raise TypeError("installed research port returned invalid convergence")
        terminal_status = self._terminal_status(convergence, state)
        state = self._record_decision(
            events,
            state_machine=state_machine,
            state=state,
            state_history=state_history,
            role="verifier",
            operation=(
                "verify_completed_research"
                if terminal_status == "completed"
                else "retain_incomplete_research"
            ),
            rationale=(
                "accept completion only when convergence and the observed evidence "
                "state contain no blocking gaps"
            ),
            observation_ids=(convergence.artifact_id,),
            evidence_ids=(),
            policy_ids=policy_ids,
            budget_decision_ids=(convergence.artifact_id,),
            terminal_status=terminal_status,
        )
        insufficiencies = self._insufficiencies(state, search, candidates)
        causal_events = tuple(events)
        return InstalledResearchResult(
            plan=plan,
            search=search,
            convergence=convergence,
            opposition_candidate_ids=candidates,
            relation_status=relation_status,
            insufficiencies=insufficiencies,
            state_history=tuple(state_history),
            final_state=state,
            tool_failure_artifact_ids=tool_failure_ids,
            causal_events=causal_events,
            causal_trace=ResearchCausalTrace.create(causal_events),
        )

    @classmethod
    def _record_decision(
        cls,
        events: list[CausalDecisionEvent],
        *,
        state_machine: ObservedResearchStateMachine,
        state: ObservedResearchState,
        state_history: list[ObservedResearchState],
        role: str,
        operation: str,
        rationale: str,
        observation_ids: tuple[str, ...],
        evidence_ids: tuple[str, ...],
        policy_ids: tuple[str, ...],
        budget_decision_ids: tuple[str, ...] = (),
        evidence_relations: tuple[InstalledEvidenceRelation, ...] | None = None,
        gaps: tuple[ObservedResearchGap, ...] | None = None,
        consume_search: bool = False,
        terminal_status: str | None = None,
    ) -> ObservedResearchState:
        decision = ObservedResearchDecision.create(
            role=role,
            operation=operation,
            rationale=rationale,
            cause_artifact_ids=(state.artifact_id,) + observation_ids + evidence_ids,
        )
        state_after = state_machine.transition(
            state,
            decision,
            evidence_relations=evidence_relations,
            gaps=gaps,
            consume_search=consume_search,
            terminal_status=terminal_status,
        )
        sequence = len(events)
        transition_id = _artifact_id(
            {
                "decision_artifact_id": decision.artifact_id,
                "from": state.artifact_id,
                "sequence": sequence,
                "to": state_after.artifact_id,
            }
        )
        events.append(
            CausalDecisionEvent.create(
                sequence=sequence,
                state_before_artifact_id=state.artifact_id,
                role=role,
                operation=operation,
                rationale=rationale,
                observation_artifact_ids=observation_ids,
                evidence_artifact_ids=evidence_ids,
                tool_decision_artifact_ids=(),
                budget_decision_artifact_ids=budget_decision_ids,
                policy_artifact_ids=policy_ids,
                output_artifact_ids=(state_after.artifact_id,),
                operation_artifact_id=decision.artifact_id,
                transition_artifact_id=transition_id,
                state_after_artifact_id=state_after.artifact_id,
            )
        )
        state_history.append(state_after)
        return state_after

    @classmethod
    def _record_search_observation(
        cls,
        *,
        events: list[CausalDecisionEvent],
        state_machine: ObservedResearchStateMachine,
        state: ObservedResearchState,
        state_history: list[ObservedResearchState],
        search: InstalledResearchSearch,
        candidates: tuple[str, ...],
        policy_ids: tuple[str, ...],
    ) -> ObservedResearchState:
        relations = list(state.evidence_relations)
        gaps = list(state.gaps)
        outcomes = {record.outcome for record in search.records}
        if candidates:
            for record in search.records:
                relation_kind = (
                    ObservedEvidenceRelationKind.AMBIGUITY
                    if "ambigu" in record.outcome
                    else ObservedEvidenceRelationKind.UNCLASSIFIED
                )
                gap_kind = (
                    ObservedResearchGapKind.AMBIGUOUS_EVIDENCE
                    if relation_kind is ObservedEvidenceRelationKind.AMBIGUITY
                    else ObservedResearchGapKind.UNCLASSIFIED_EVIDENCE
                )
                for evidence_id in record.candidate_evidence_artifact_ids:
                    record_relations = tuple(
                        InstalledEvidenceRelation.create(
                            claim_artifact_id=claim_id,
                            evidence_artifact_id=evidence_id,
                            kind=relation_kind,
                            material=True,
                        )
                        for claim_id in record.effective_target_claim_artifact_ids
                    )
                    relations.extend(record_relations)
                    gaps.append(
                        ObservedResearchGap.create(
                            kind=gap_kind,
                            subject_artifact_id=(
                                record_relations[0].artifact_id
                                if record_relations
                                else evidence_id
                            ),
                        )
                    )
            state = cls._record_decision(
                events,
                state_machine=state_machine,
                state=state,
                state_history=state_history,
                role="skeptic",
                operation="inspect_material_counterevidence",
                rationale=(
                    "material retrieved candidates require explicit semantic relation "
                    "assessment"
                ),
                observation_ids=(search.artifact_id,),
                evidence_ids=candidates,
                policy_ids=policy_ids,
                evidence_relations=tuple(relations),
                gaps=tuple(gaps),
            )
            return cls._record_decision(
                events,
                state_machine=state_machine,
                state=state,
                state_history=state_history,
                role="adjudicator",
                operation="retain_unclassified_material_evidence",
                rationale=(
                    "do not revise or complete the answer until every material "
                    "candidate has a classified relation"
                ),
                observation_ids=tuple(gap.artifact_id for gap in state.blocking_gaps),
                evidence_ids=candidates,
                policy_ids=policy_ids,
            )
        if "retrieval_refused" in outcomes:
            gap = ObservedResearchGap.create(
                kind=ObservedResearchGapKind.RETRIEVAL_REFUSED,
                subject_artifact_id=search.artifact_id,
            )
            return cls._record_decision(
                events,
                state_machine=state_machine,
                state=state,
                state_history=state_history,
                role="adjudicator",
                operation="retain_retrieval_refusal",
                rationale=(
                    "a refused retrieval leaves its evidence need unresolved and "
                    "cannot count as a negative result"
                ),
                observation_ids=(search.artifact_id,),
                evidence_ids=(),
                policy_ids=policy_ids,
                gaps=state.gaps + (gap,),
            )
        if any("ambigu" in outcome for outcome in outcomes):
            gap = ObservedResearchGap.create(
                kind=ObservedResearchGapKind.AMBIGUOUS_EVIDENCE,
                subject_artifact_id=search.artifact_id,
            )
            return cls._record_decision(
                events,
                state_machine=state_machine,
                state=state,
                state_history=state_history,
                role="adjudicator",
                operation="retain_ambiguous_evidence",
                rationale="ambiguous evidence requires adjudication before synthesis",
                observation_ids=(search.artifact_id,),
                evidence_ids=(),
                policy_ids=policy_ids,
                gaps=state.gaps + (gap,),
            )
        no_result_gap = ObservedResearchGap.create(
            kind=ObservedResearchGapKind.NO_RESULTS,
            subject_artifact_id=search.artifact_id,
            blocking=False,
        )
        for claim_id in search.unsearched_important_claim_artifact_ids:
            gaps.append(
                ObservedResearchGap.create(
                    kind=ObservedResearchGapKind.UNSEARCHED_IMPORTANT_CLAIM,
                    subject_artifact_id=claim_id,
                )
            )
        return cls._record_decision(
            events,
            state_machine=state_machine,
            state=state,
            state_history=state_history,
            role="verifier",
            operation="retain_bounded_negative_search",
            rationale=(
                "retain the bounded no-result observation without interpreting it "
                "as confirmation"
            ),
            observation_ids=(search.artifact_id,),
            evidence_ids=(),
            policy_ids=policy_ids,
            gaps=tuple(gaps) + (no_result_gap,),
        )

    @staticmethod
    def _relation_status(
        state: ObservedResearchState,
        search: InstalledResearchSearch | None,
        tool_failure_ids: tuple[str, ...],
    ) -> str:
        if tool_failure_ids:
            return "tool-failure"
        kinds = {relation.kind for relation in state.evidence_relations}
        if ObservedEvidenceRelationKind.UNCLASSIFIED in kinds:
            return "unclassified"
        if ObservedEvidenceRelationKind.AMBIGUITY in kinds or any(
            gap.kind is ObservedResearchGapKind.AMBIGUOUS_EVIDENCE
            for gap in state.gaps
        ):
            return "ambiguous"
        if any(
            gap.kind is ObservedResearchGapKind.RETRIEVAL_REFUSED
            for gap in state.gaps
        ):
            return "retrieval-refused"
        if search is None and not state.blocking_gaps:
            return "sufficient-evidence"
        return "no-new-counterevidence"

    @staticmethod
    def _terminal_status(
        convergence: InstalledResearchConvergence,
        state: ObservedResearchState,
    ) -> str:
        if convergence.stop and convergence.outcome == "converged":
            return "completed" if not state.blocking_gaps else "incomplete"
        if convergence.stop and convergence.outcome == "insufficient":
            return "insufficient"
        return "incomplete"

    @staticmethod
    def _insufficiencies(
        state: ObservedResearchState,
        search: InstalledResearchSearch | None,
        candidates: tuple[str, ...],
    ) -> tuple[str, ...]:
        findings = tuple(
            record.negative_search_statement
            for record in (() if search is None else search.records)
            if record.negative_search_statement is not None
        )
        if candidates:
            findings += (
                "Counterevidence candidates require relation classification before use.",
            )
        if search is not None and any(
            record.outcome == "retrieval_refused" for record in search.records
        ):
            findings += ("One or more skeptical retrievals were refused.",)
        gap_messages = {
            ObservedResearchGapKind.UNSATISFIED_REQUIREMENT: (
                "One or more answer requirements remain unsatisfied."
            ),
            ObservedResearchGapKind.MATERIAL_OPPOSITION: (
                "Material opposition remains unresolved."
            ),
            ObservedResearchGapKind.AMBIGUOUS_EVIDENCE: (
                "Ambiguous evidence requires adjudication."
            ),
            ObservedResearchGapKind.UNCLASSIFIED_EVIDENCE: (
                "Material evidence remains unclassified."
            ),
            ObservedResearchGapKind.RETRIEVAL_REFUSED: (
                "One or more skeptical retrievals were refused."
            ),
            ObservedResearchGapKind.UNSEARCHED_IMPORTANT_CLAIM: (
                "One or more important claims remain unsearched."
            ),
            ObservedResearchGapKind.TOOL_FAILURE: (
                "A research tool failed before producing admissible evidence."
            ),
        }
        findings += tuple(
            message
            for kind, message in gap_messages.items()
            if any(gap.kind is kind for gap in state.gaps)
        )
        if search is None and state.blocking_gaps:
            findings += ("No executable search resolved the blocking evidence gaps.",)
        return tuple(dict.fromkeys(findings))


__all__ = [
    "InstalledResearchClaim",
    "InstalledResearchConvergence",
    "InstalledResearchPlan",
    "InstalledResearchPort",
    "InstalledResearchRequest",
    "InstalledResearchResult",
    "InstalledResearchSearch",
    "InstalledResearchSearchRecord",
    "InstalledResearchService",
]
