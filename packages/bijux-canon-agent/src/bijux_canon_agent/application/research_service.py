"""Agent-owned orchestration for installed counterevidence research."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
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
    TargetedSearchAttempt,
    TargetedSearchObservation,
    TargetedSearchOutcome,
    TargetedSearchPlan,
    TargetedSearchPlanningService,
    TargetedSearchPolicy,
)
from bijux_canon_agent.application.research_workflow.terminal_outcome import (
    InstalledResearchTerminalKind,
    InstalledResearchTerminalOutcome,
    RemainingResearchWork,
)
from bijux_canon_agent.contracts.research_budget import (
    BudgetAction,
    BudgetDecision,
    BudgetDimensions,
    ResearchBudgetLedger,
    ResearchBudgetPolicy,
)
from bijux_canon_agent.contracts.execution_control import (
    CancellationPort,
    CancellationSignal,
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
    budget_limits: BudgetDimensions
    maximum_search_candidates: int
    grounding_admission_outcome: str = "admitted"

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
        if not isinstance(self.budget_limits, BudgetDimensions):
            raise TypeError("installed research budget limits are invalid")
        if self.maximum_search_candidates < 1:
            raise ValueError("maximum search candidates must be positive")
        claim_ids = {claim.artifact_id for claim in self.claims}
        finding_claim_ids = tuple(
            item.claim_artifact_id
            for item in self.requirements
            if item.kind == "finding" and item.claim_artifact_id is not None
        )
        if set(finding_claim_ids) != claim_ids or len(finding_claim_ids) != len(
            set(finding_claim_ids)
        ):
            raise ValueError("finding requirements must cover every claim exactly once")
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
        if self.grounding_admission_outcome not in {
            "admitted",
            "partially_admitted",
            "abstained",
        }:
            raise ValueError("grounding admission outcome is invalid")
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
    execution_usage: BudgetDimensions = BudgetDimensions()

    def __post_init__(self) -> None:
        _require_artifact_id(self.artifact_id, "research plan artifact_id")
        for artifact_id in self.request_artifact_ids:
            _require_artifact_id(artifact_id, "research request artifact_id")
        if not isinstance(self.record, Mapping):
            raise TypeError("research plan record must be a mapping")
        if not isinstance(self.execution_usage, BudgetDimensions):
            raise TypeError("research plan execution usage is invalid")
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
    classifications: tuple[InstalledCandidateClassification, ...] = ()

    def __post_init__(self) -> None:
        _require_artifact_id(self.claim_artifact_id, "searched claim artifact_id")
        if not self.outcome:
            raise ValueError("research search outcome must not be empty")
        for artifact_id in self.candidate_evidence_artifact_ids:
            _require_artifact_id(artifact_id, "candidate evidence artifact_id")
        for artifact_id in (
            (
                ()
                if self.requirement_artifact_id is None
                else (self.requirement_artifact_id,)
            )
            + (
                ()
                if self.target_claim_artifact_ids is None
                else self.target_claim_artifact_ids
            )
            + (() if self.attempt_artifact_id is None else (self.attempt_artifact_id,))
        ):
            _require_artifact_id(artifact_id, "targeted search record reference")
        if not isinstance(self.record, Mapping):
            raise TypeError("research search record must be a mapping")
        candidate_ids = set(self.candidate_evidence_artifact_ids)
        classified_ids = {item.evidence_artifact_id for item in self.classifications}
        if self.classifications and classified_ids != candidate_ids:
            raise ValueError("research candidate classifications are incomplete")

    @property
    def effective_target_claim_artifact_ids(self) -> tuple[str, ...]:
        """Return explicit claim targets or the compatibility claim target."""
        return (
            (self.claim_artifact_id,)
            if self.target_claim_artifact_ids is None
            else self.target_claim_artifact_ids
        )


@dataclass(frozen=True, slots=True)
class InstalledCandidateClassification:
    """Reason-owned candidate relation projected into Agent workflow state."""

    artifact_id: str
    requirement_artifact_id: str
    claim_artifact_id: str | None
    evidence_artifact_id: str
    relation: str
    rationale: str
    method: str
    confidence: float
    material: bool
    record: Mapping[str, object]

    def __post_init__(self) -> None:
        for value, field in (
            (self.artifact_id, "candidate classification artifact_id"),
            (self.requirement_artifact_id, "classified requirement artifact_id"),
            (self.evidence_artifact_id, "classified evidence artifact_id"),
        ):
            _require_artifact_id(value, field)
        if self.claim_artifact_id is not None:
            _require_artifact_id(self.claim_artifact_id, "classified claim artifact_id")
        if (
            not self.relation
            or not self.rationale
            or not self.method
            or not 0 <= self.confidence <= 1
        ):
            raise ValueError("candidate classification semantics are invalid")
        if not isinstance(self.record, Mapping):
            raise TypeError("candidate classification record must be a mapping")


@dataclass(frozen=True, slots=True)
class InstalledResearchSearch:
    """Complete search output plus persisted Runtime retrieval artifacts."""

    artifact_id: str
    document_artifact_ids: tuple[str, ...]
    records: tuple[InstalledResearchSearchRecord, ...]
    unsearched_important_claim_artifact_ids: tuple[str, ...]
    retrieval_artifact_ids: tuple[str, ...]
    retrieval_records: tuple[Mapping[str, object], ...]
    record: Mapping[str, object]
    adjudication_records: tuple[Mapping[str, object], ...] = ()
    execution_usage: BudgetDimensions = BudgetDimensions()

    def __post_init__(self) -> None:
        _require_artifact_id(self.artifact_id, "research search artifact_id")
        if len(self.document_artifact_ids) != len(set(self.document_artifact_ids)):
            raise ValueError("research search document identities must be unique")
        for artifact_id in self.document_artifact_ids:
            _require_artifact_id(artifact_id, "research search document artifact_id")
        for artifact_id in self.unsearched_important_claim_artifact_ids:
            _require_artifact_id(artifact_id, "unsearched claim artifact_id")
        for artifact_id in self.retrieval_artifact_ids:
            _require_artifact_id(artifact_id, "retrieval artifact_id")
        if any(not isinstance(item, Mapping) for item in self.retrieval_records):
            raise TypeError("research retrieval records must be mappings")
        if not isinstance(self.record, Mapping):
            raise TypeError("research search output must be a mapping")
        if any(not isinstance(item, Mapping) for item in self.adjudication_records):
            raise TypeError("research adjudication records must be mappings")
        if not isinstance(self.execution_usage, BudgetDimensions):
            raise TypeError("research search execution usage is invalid")


@dataclass(frozen=True, slots=True)
class InstalledResearchConvergence:
    """Typed convergence decision returned by the reasoning port."""

    artifact_id: str
    outcome: str
    stop: bool
    record: Mapping[str, object]
    execution_usage: BudgetDimensions = BudgetDimensions()

    def __post_init__(self) -> None:
        _require_artifact_id(self.artifact_id, "research convergence artifact_id")
        if not self.outcome:
            raise ValueError("research convergence outcome must not be empty")
        if not isinstance(self.record, Mapping):
            raise TypeError("research convergence record must be a mapping")
        if not isinstance(self.execution_usage, BudgetDimensions):
            raise TypeError("research convergence execution usage is invalid")


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
    plan_history: tuple[InstalledResearchPlan, ...]
    search_history: tuple[InstalledResearchSearch, ...]
    targeted_search_observations: tuple[TargetedSearchObservation, ...]
    budget_policy: ResearchBudgetPolicy
    budget_policy_artifact_id: str
    budget_decisions: tuple[BudgetDecision, ...]
    budget_usage: BudgetDimensions
    cancellation_signal: CancellationSignal | None
    terminal_outcome: InstalledResearchTerminalOutcome


class InstalledResearchService:
    """Choose and execute installed research operations through typed ports."""

    @staticmethod
    def _budget_policy(request: InstalledResearchRequest) -> ResearchBudgetPolicy:
        plan_payload = {
            "claim_graph_artifact_id": request.claim_graph_artifact_id,
            "scope_artifact_id": request.scope_artifact_id,
            "counterevidence_policy_artifact_id": (
                request.counterevidence_policy_artifact_id
            ),
            "convergence_policy_artifact_id": request.convergence_policy_artifact_id,
            "requirement_plan_artifact_id": request.requirement_plan_artifact_id,
            "max_searches": request.max_searches,
            "maximum_search_candidates": request.maximum_search_candidates,
            "budget_limits": request.budget_limits.payload(),
        }
        role_limits = BudgetDimensions(
            **{
                name: value + max(1, value)
                for name, value in request.budget_limits.payload().items()
            }
        )
        return ResearchBudgetPolicy(
            plan_sha256=hashlib.sha256(_canonical(plan_payload)).hexdigest(),
            global_limits=request.budget_limits,
            role_limits={
                "plan": role_limits,
                "search": role_limits,
                "evaluate": role_limits,
            },
        )

    @staticmethod
    def _output_charge(
        value: object,
        *,
        documents: int = 0,
        candidates: int = 0,
        evidence_items: int = 0,
    ) -> BudgetDimensions:
        size = len(_canonical(value))
        return BudgetDimensions(
            documents=documents,
            candidates=candidates,
            evidence_items=evidence_items,
            memory_bytes=size,
            artifact_bytes=size,
        )

    @staticmethod
    def _reservation(
        budget: ResearchBudgetLedger,
        *,
        role: str,
        label: str,
        start: BudgetDimensions,
        candidates: int = 0,
    ) -> BudgetDecision:
        capacity = budget.remaining(role=role)
        return budget.reserve(
            role=role,
            label=f"{label}:reserve",
            maximum=start.plus(
                BudgetDimensions(
                    documents=candidates,
                    candidates=candidates,
                    evidence_items=candidates,
                    provider_calls=capacity.provider_calls,
                    tokens=capacity.tokens,
                    elapsed_ms=capacity.elapsed_ms,
                    retries=capacity.retries,
                    memory_bytes=capacity.memory_bytes,
                    artifact_bytes=capacity.artifact_bytes,
                )
            ),
        )

    @staticmethod
    def _budget_plan(
        decision: BudgetDecision,
        targeted_search_plan: TargetedSearchPlan | None,
        rejected_plan_artifact_id: str | None = None,
    ) -> InstalledResearchPlan:
        record: dict[str, object] = {
            "budget_decision_artifact_id": decision.artifact_id,
            "outcome": "budget_exhausted",
            "rejected_plan_artifact_id": rejected_plan_artifact_id,
            "request_artifact_ids": [],
            "targeted_search_plan_artifact_id": (
                None
                if targeted_search_plan is None
                else targeted_search_plan.artifact_id
            ),
        }
        return InstalledResearchPlan(
            artifact_id=_artifact_id(record),
            request_artifact_ids=(),
            record=record,
            targeted_search_plan=None,
        )

    @staticmethod
    def _budget_convergence(
        request: InstalledResearchRequest,
        decision: BudgetDecision,
    ) -> InstalledResearchConvergence:
        identity_record = {
            "budget_decision_artifact_id": decision.artifact_id,
            "claim_graph_artifact_id": request.claim_graph_artifact_id,
            "outcome": "budget_exhausted",
            "stop": True,
        }
        artifact_id = _artifact_id(identity_record)
        record = {"artifact_id": artifact_id, **identity_record}
        return InstalledResearchConvergence(
            artifact_id=artifact_id,
            outcome="budget_exhausted",
            stop=True,
            record=record,
        )

    @staticmethod
    def _cancellation_plan(
        request: InstalledResearchRequest,
        signal: CancellationSignal,
    ) -> InstalledResearchPlan:
        record: dict[str, object] = {
            "cancellation_artifact_id": signal.artifact_id,
            "claim_graph_artifact_id": request.claim_graph_artifact_id,
            "outcome": "cancelled",
            "request_artifact_ids": [],
        }
        return InstalledResearchPlan(
            artifact_id=_artifact_id(record),
            request_artifact_ids=(),
            record=record,
        )

    @staticmethod
    def _cancellation_convergence(
        request: InstalledResearchRequest,
        signal: CancellationSignal,
    ) -> InstalledResearchConvergence:
        identity_record: dict[str, object] = {
            "cancellation_artifact_id": signal.artifact_id,
            "claim_graph_artifact_id": request.claim_graph_artifact_id,
            "outcome": "cancelled",
            "stop": True,
        }
        artifact_id = _artifact_id(identity_record)
        record = {"artifact_id": artifact_id, **identity_record}
        return InstalledResearchConvergence(
            artifact_id=artifact_id,
            outcome="cancelled",
            stop=True,
            record=record,
        )

    @staticmethod
    def _cancellation(
        cancellation_port: CancellationPort | None,
    ) -> CancellationSignal:
        signal = (
            CancellationSignal.inactive()
            if cancellation_port is None
            else cancellation_port.current()
        )
        if not isinstance(signal, CancellationSignal):
            raise TypeError("installed cancellation port returned an invalid signal")
        return signal

    def research(
        self,
        request: InstalledResearchRequest,
        port: InstalledResearchPort,
        cancellation_port: CancellationPort | None = None,
    ) -> InstalledResearchResult:
        """Run only operations justified by the current plan and observations."""
        if not isinstance(request, InstalledResearchRequest):
            raise TypeError("installed research request has the wrong type")
        if not isinstance(port, InstalledResearchPort):
            raise TypeError("installed research port does not implement its contract")
        if cancellation_port is not None and not isinstance(
            cancellation_port, CancellationPort
        ):
            raise TypeError("installed cancellation port does not implement its contract")
        events: list[CausalDecisionEvent] = []
        budget = ResearchBudgetLedger(self._budget_policy(request))
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
            budget.policy.artifact_id,
        )
        targeted_planner = (
            None
            if request.max_searches == 0
            else TargetedSearchPlanningService(
                TargetedSearchPolicy(
                    max_attempts=request.max_searches,
                    max_attempts_per_requirement=min(2, request.max_searches),
                )
            )
        )
        attempts: list[TargetedSearchAttempt] = []
        targeted_observations: list[TargetedSearchObservation] = []
        plans: list[InstalledResearchPlan] = []
        searches: list[InstalledResearchSearch] = []
        search: InstalledResearchSearch | None = None
        tool_failures: list[str] = []
        candidates: tuple[str, ...] = ()
        cancellation_signal: CancellationSignal | None = None
        cancellation_budget_decision_ids: tuple[str, ...] = ()
        cancellation_consumed_search = False
        while True:
            signal = self._cancellation(cancellation_port)
            if signal.requested:
                cancellation_signal = signal
                if not plans:
                    plans.append(self._cancellation_plan(request, signal))
                break
            targeted_search_plan = (
                None
                if targeted_planner is None
                else targeted_planner.plan(
                    state.requirements,
                    attempts=tuple(attempts),
                    observations=tuple(targeted_observations),
                )
            )
            if (
                targeted_search_plan is not None
                and targeted_search_plan.attempt is None
                and plans
            ):
                state = self._record_decision(
                    events,
                    state_machine=state_machine,
                    state=state,
                    state_history=state_history,
                    role="adjudicator",
                    operation="retain_unresolved_requirements",
                    rationale=(
                        "observed results justify no distinct additional query "
                        "within the targeted-search policy"
                    ),
                    observation_ids=(targeted_search_plan.artifact_id,),
                    evidence_ids=(),
                    policy_ids=policy_ids,
                )
                break
            plan_budget_start = len(budget.decisions)
            plan_start_usage = BudgetDimensions(iterations=1)
            plan_reservation = self._reservation(
                budget,
                role="plan",
                label="plan_counterevidence",
                start=plan_start_usage,
            )
            if plan_reservation.action is BudgetAction.TERMINATE:
                plan = self._budget_plan(
                    plan_reservation,
                    targeted_search_plan,
                )
                plans.append(plan)
                state = self._record_decision(
                    events,
                    state_machine=state_machine,
                    state=state,
                    state_history=state_history,
                    role="plan",
                    operation="refuse_unbudgeted_plan",
                    rationale="do not call the planning port without a reserved output envelope",
                    observation_ids=(plan.artifact_id,),
                    evidence_ids=(),
                    policy_ids=policy_ids,
                    budget_decision_ids=tuple(
                        item.artifact_id
                        for item in budget.decisions[plan_budget_start:]
                    ),
                )
                break
            budget.charge(
                role="plan",
                label="plan_counterevidence:start",
                usage=plan_start_usage,
            )
            try:
                plan = port.plan(request, targeted_search_plan)
            except Exception:
                signal = self._cancellation(cancellation_port)
                if not signal.requested:
                    raise
                cancellation_signal = signal
                cancellation_budget_decision_ids = tuple(
                    item.artifact_id
                    for item in budget.decisions[plan_budget_start:]
                )
                plans.append(self._cancellation_plan(request, signal))
                break
            if not isinstance(plan, InstalledResearchPlan):
                raise TypeError("installed research port returned an invalid plan")
            plan_finish = budget.charge(
                role="plan",
                label="plan_counterevidence:finish",
                usage=self._output_charge(asdict(plan)).plus(plan.execution_usage),
            )
            if plan_finish.action is BudgetAction.TERMINATE:
                plan = self._budget_plan(
                    plan_finish,
                    targeted_search_plan,
                    rejected_plan_artifact_id=plan.artifact_id,
                )
                plans.append(plan)
                state = self._record_decision(
                    events,
                    state_machine=state_machine,
                    state=state,
                    state_history=state_history,
                    role="plan",
                    operation="refuse_oversized_plan_result",
                    rationale="do not admit a planning result that exceeds its reserved envelope",
                    observation_ids=(plan.artifact_id,),
                    evidence_ids=(),
                    policy_ids=policy_ids,
                    budget_decision_ids=tuple(
                        item.artifact_id
                        for item in budget.decisions[plan_budget_start:]
                    ),
                )
                break
            plans.append(plan)
            state = self._record_decision(
                events,
                state_machine=state_machine,
                state=state,
                state_history=state_history,
                role="plan",
                operation="plan_counterevidence",
                rationale=(
                    "select the highest-priority unresolved answer requirement "
                    "with a distinct query justified by observed search outcomes"
                ),
                observation_ids=(plan.artifact_id,),
                evidence_ids=(),
                policy_ids=policy_ids,
                budget_decision_ids=tuple(
                    item.artifact_id
                    for item in budget.decisions[plan_budget_start:]
                ),
            )
            signal = self._cancellation(cancellation_port)
            if signal.requested:
                cancellation_signal = signal
                break
            if (
                not plan.request_artifact_ids
                or state.search_budget_used >= state.search_budget_limit
            ):
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
                        "the observed requirements are already satisfied, so an "
                        "additional search is not needed"
                        if not state.blocking_gaps
                        else "the plan exposed no distinct executable search for blocking gaps"
                    ),
                    observation_ids=(plan.artifact_id,),
                    evidence_ids=(),
                    policy_ids=policy_ids,
                )
                break
            search = None
            signal = self._cancellation(cancellation_port)
            if signal.requested:
                cancellation_signal = signal
                break
            search_budget_start = len(budget.decisions)
            search_start_usage = BudgetDimensions(
                iterations=1,
                retrievals=1,
                tool_calls=1,
            )
            search_reservation = self._reservation(
                budget,
                role="search",
                label="search_counterevidence",
                start=search_start_usage,
                candidates=request.maximum_search_candidates,
            )
            if search_reservation.action is BudgetAction.TERMINATE:
                state = self._record_decision(
                    events,
                    state_machine=state_machine,
                    state=state,
                    state_history=state_history,
                    role="researcher",
                    operation="refuse_unbudgeted_search",
                    rationale="do not call retrieval without its complete reserved resource envelope",
                    observation_ids=(search_reservation.artifact_id,),
                    evidence_ids=(),
                    policy_ids=policy_ids,
                    budget_decision_ids=tuple(
                        item.artifact_id
                        for item in budget.decisions[search_budget_start:]
                    ),
                )
                break
            budget.charge(
                role="search",
                label="search_counterevidence:start",
                usage=search_start_usage,
            )
            try:
                search = port.search(request, plan)
                if not isinstance(search, InstalledResearchSearch):
                    raise TypeError(
                        "installed research port returned an invalid search"
                    )
            except Exception as error:
                signal = self._cancellation(cancellation_port)
                if signal.requested:
                    cancellation_signal = signal
                    cancellation_budget_decision_ids = tuple(
                        item.artifact_id
                        for item in budget.decisions[search_budget_start:]
                    )
                    cancellation_consumed_search = True
                    break
                failure_id = _artifact_id(
                    {
                        "error_type": type(error).__name__,
                        "operation": "search_counterevidence",
                        "plan_artifact_id": plan.artifact_id,
                    }
                )
                tool_failures.append(failure_id)
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
                    budget_decision_ids=tuple(
                        item.artifact_id
                        for item in budget.decisions[search_budget_start:]
                    ),
                    gaps=state.gaps + (failure_gap,),
                    consume_search=True,
                )
                break
            search_candidates = tuple(
                artifact_id
                for record in search.records
                for artifact_id in record.candidate_evidence_artifact_ids
            )
            search_finish = budget.charge(
                role="search",
                label="search_counterevidence:finish",
                usage=self._output_charge(
                    asdict(search),
                    documents=len(search.document_artifact_ids),
                    candidates=len(search_candidates),
                    evidence_items=len(search_candidates),
                ).plus(search.execution_usage),
            )
            if search_finish.action is BudgetAction.TERMINATE:
                search = None
                state = self._record_decision(
                    events,
                    state_machine=state_machine,
                    state=state,
                    state_history=state_history,
                    role="researcher",
                    operation="refuse_oversized_search_result",
                    rationale="retain the attempted call but do not admit evidence beyond the reserved budget",
                    observation_ids=(search_finish.artifact_id,),
                    evidence_ids=(),
                    policy_ids=policy_ids,
                    budget_decision_ids=tuple(
                        item.artifact_id
                        for item in budget.decisions[search_budget_start:]
                    ),
                    consume_search=True,
                )
                break
            searches.append(search)
            state = self._record_decision(
                events,
                state_machine=state_machine,
                state=state,
                state_history=state_history,
                role="researcher",
                operation="search_counterevidence",
                rationale=(
                    "execute the selected requirement-specific query because its "
                    "recorded evidence need remains unresolved"
                ),
                observation_ids=(search.artifact_id,),
                evidence_ids=(),
                policy_ids=policy_ids,
                budget_decision_ids=tuple(
                    item.artifact_id
                    for item in budget.decisions[search_budget_start:]
                ),
                consume_search=True,
            )
            candidates += search_candidates
            state = self._record_search_observation(
                events=events,
                state_machine=state_machine,
                state=state,
                state_history=state_history,
                search=search,
                candidates=search_candidates,
                policy_ids=policy_ids,
            )
            attempt = (
                None if targeted_search_plan is None else targeted_search_plan.attempt
            )
            if attempt is None:
                raise TypeError("executed research plan has no targeted search attempt")
            attempts.append(attempt)
            observation = self._targeted_observation(attempt, search)
            targeted_observations.append(observation)
            signal = self._cancellation(cancellation_port)
            if signal.requested:
                cancellation_signal = signal
                break
            if observation.outcome in {
                TargetedSearchOutcome.MATERIAL_CANDIDATE,
                TargetedSearchOutcome.REFUSED,
            }:
                break

        plan = plans[-1]
        tool_failure_ids = tuple(tool_failures)
        relation_status = self._relation_status(state, search, tool_failure_ids)
        evaluation_budget_start = len(budget.decisions)
        cancellation_observation_ids: tuple[str, ...] = ()
        if cancellation_signal is None:
            signal = self._cancellation(cancellation_port)
            if signal.requested:
                cancellation_signal = signal
        if cancellation_signal is not None:
            convergence = self._cancellation_convergence(
                request,
                cancellation_signal,
            )
        elif budget.exhausted_dimensions:
            convergence = self._budget_convergence(request, budget.decisions[-1])
        else:
            evaluation_start_usage = BudgetDimensions(iterations=1)
            evaluation_reservation = self._reservation(
                budget,
                role="evaluate",
                label="evaluate_convergence",
                start=evaluation_start_usage,
            )
            if evaluation_reservation.action is BudgetAction.TERMINATE:
                convergence = self._budget_convergence(
                    request,
                    evaluation_reservation,
                )
            else:
                budget.charge(
                    role="evaluate",
                    label="evaluate_convergence:start",
                    usage=evaluation_start_usage,
                )
                try:
                    convergence = port.evaluate(request, plan, search)
                except Exception:
                    signal = self._cancellation(cancellation_port)
                    if not signal.requested:
                        raise
                    cancellation_signal = signal
                    cancellation_budget_decision_ids = tuple(
                        item.artifact_id
                        for item in budget.decisions[evaluation_budget_start:]
                    )
                    convergence = self._cancellation_convergence(request, signal)
                if not isinstance(convergence, InstalledResearchConvergence):
                    raise TypeError(
                        "installed research port returned invalid convergence"
                    )
                if cancellation_signal is None:
                    evaluation_finish = budget.charge(
                        role="evaluate",
                        label="evaluate_convergence:finish",
                        usage=self._output_charge(asdict(convergence)).plus(
                            convergence.execution_usage
                        ),
                    )
                    if evaluation_finish.action is BudgetAction.TERMINATE:
                        convergence = self._budget_convergence(
                            request,
                            evaluation_finish,
                        )
                    else:
                        signal = self._cancellation(cancellation_port)
                        if signal.requested:
                            cancellation_signal = signal
                            cancellation_budget_decision_ids = tuple(
                                item.artifact_id
                                for item in budget.decisions[
                                    evaluation_budget_start:
                                ]
                            )
                            cancellation_observation_ids = (
                                convergence.artifact_id,
                            )
                            convergence = self._cancellation_convergence(
                                request,
                                signal,
                            )
        if cancellation_signal is not None:
            terminal_status = "incomplete"
            state = self._record_decision(
                events,
                state_machine=state_machine,
                state=state,
                state_history=state_history,
                role="controller",
                operation="cancel_research",
                rationale="stop before any later call while retaining completed in-flight evidence",
                observation_ids=(cancellation_signal.artifact_id, plan.artifact_id)
                + cancellation_observation_ids,
                evidence_ids=(),
                policy_ids=policy_ids,
                budget_decision_ids=cancellation_budget_decision_ids,
                consume_search=cancellation_consumed_search,
                terminal_status=terminal_status,
            )
        else:
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
                budget_decision_ids=tuple(
                    item.artifact_id
                    for item in budget.decisions[evaluation_budget_start:]
                ),
                terminal_status=terminal_status,
            )
        insufficiencies = self._insufficiencies(state, search, candidates)
        remaining_work = self._remaining_work(
            state=state,
            searches=tuple(searches),
            insufficiencies=insufficiencies,
            budget_exhaustion_artifact_id=(
                None
                if not budget.exhausted_dimensions
                else budget.decisions[-1].artifact_id
            ),
        )
        exhausted_dimensions = budget.exhausted_dimensions or (
            ("retrievals",)
            if remaining_work.pending
            and state.search_budget_used >= state.search_budget_limit
            and (
                remaining_work.unsatisfied_requirement_artifact_ids
                or remaining_work.unsearched_important_claim_artifact_ids
            )
            else ()
        )
        if cancellation_signal is not None:
            terminal_kind = InstalledResearchTerminalKind.CANCELLED
        elif tool_failure_ids:
            terminal_kind = InstalledResearchTerminalKind.FAILED
        elif exhausted_dimensions:
            terminal_kind = InstalledResearchTerminalKind.INCOMPLETE_BUDGET
        elif (
            request.grounding_admission_outcome == "abstained" or remaining_work.pending
        ):
            terminal_kind = InstalledResearchTerminalKind.ABSTAINED
        else:
            terminal_kind = InstalledResearchTerminalKind.CONVERGED
        terminal_outcome = InstalledResearchTerminalOutcome.create(
            kind=terminal_kind,
            convergence_artifact_id=convergence.artifact_id,
            convergence_outcome=convergence.outcome,
            remaining_work=remaining_work,
            exhausted_budget_dimensions=exhausted_dimensions,
            cancellation_artifact_id=(
                None
                if cancellation_signal is None
                else cancellation_signal.artifact_id
            ),
            failure_artifact_ids=tool_failure_ids,
        )
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
            plan_history=tuple(plans),
            search_history=tuple(searches),
            targeted_search_observations=tuple(targeted_observations),
            budget_policy=budget.policy,
            budget_policy_artifact_id=budget.policy.artifact_id,
            budget_decisions=budget.decisions,
            budget_usage=budget.global_usage,
            cancellation_signal=cancellation_signal,
            terminal_outcome=terminal_outcome,
        )

    @staticmethod
    def _remaining_work(
        *,
        state: ObservedResearchState,
        searches: tuple[InstalledResearchSearch, ...],
        insufficiencies: tuple[str, ...],
        budget_exhaustion_artifact_id: str | None = None,
    ) -> RemainingResearchWork:
        unresolved_evidence = tuple(
            dict.fromkeys(
                classification.evidence_artifact_id
                for search in searches
                for record in search.records
                for classification in record.classifications
                if classification.material
                and classification.relation in {"ambiguous", "unclassified"}
            )
        )
        classified_evidence = {
            classification.evidence_artifact_id
            for search in searches
            for record in search.records
            for classification in record.classifications
        }
        unresolved_evidence += tuple(
            dict.fromkeys(
                artifact_id
                for search in searches
                for record in search.records
                for artifact_id in record.candidate_evidence_artifact_ids
                if artifact_id not in classified_evidence
                and artifact_id not in unresolved_evidence
            )
        )
        return RemainingResearchWork.create(
            unsatisfied_requirement_artifact_ids=tuple(
                item.artifact_id
                for item in state.requirements
                if item.material and not item.satisfied
            ),
            unresolved_evidence_artifact_ids=unresolved_evidence,
            unresolved_gap_artifact_ids=tuple(
                item.artifact_id for item in state.blocking_gaps
            )
            + (
                ()
                if budget_exhaustion_artifact_id is None or state.blocking_gaps
                else (budget_exhaustion_artifact_id,)
            ),
            unsearched_important_claim_artifact_ids=tuple(
                dict.fromkeys(
                    artifact_id
                    for search in searches
                    for artifact_id in search.unsearched_important_claim_artifact_ids
                )
            ),
            descriptions=insufficiencies,
        )

    @staticmethod
    def _targeted_observation(
        attempt: TargetedSearchAttempt,
        search: InstalledResearchSearch,
    ) -> TargetedSearchObservation:
        outcomes = {record.outcome for record in search.records}
        candidates = tuple(
            artifact_id
            for record in search.records
            for artifact_id in record.candidate_evidence_artifact_ids
        )
        evidence: tuple[str, ...]
        classifications = tuple(
            item for record in search.records for item in record.classifications
        )
        if classifications and all(
            item.relation not in {"ambiguous", "unclassified"}
            for item in classifications
        ):
            opposing = tuple(
                item.evidence_artifact_id
                for item in classifications
                if item.relation == "opposing" and item.material
            )
            supporting = tuple(
                item.evidence_artifact_id
                for item in classifications
                if item.relation in {"supporting", "limiting"} and item.material
            )
            if opposing:
                outcome = TargetedSearchOutcome.OPPOSITION
                evidence = opposing
            elif supporting:
                outcome = TargetedSearchOutcome.SUPPORT
                evidence = supporting
            else:
                outcome = TargetedSearchOutcome.NO_RESULTS
                evidence = ()
        elif any("ambigu" in outcome for outcome in outcomes):
            outcome = TargetedSearchOutcome.AMBIGUOUS
            evidence = ()
        elif candidates:
            outcome = TargetedSearchOutcome.MATERIAL_CANDIDATE
            evidence = candidates
        elif "retrieval_refused" in outcomes:
            outcome = TargetedSearchOutcome.REFUSED
            evidence = ()
        else:
            outcome = TargetedSearchOutcome.NO_RESULTS
            evidence = ()
        return TargetedSearchObservation.create(
            attempt_artifact_id=attempt.artifact_id,
            outcome=outcome,
            evidence_artifact_ids=evidence,
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
        requirements: tuple[InstalledResearchRequirement, ...] | None = None,
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
            requirements=requirements,
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
                classifications = record.classifications or tuple(
                    InstalledCandidateClassification(
                        artifact_id=_artifact_id(
                            {
                                "evidence_artifact_id": evidence_id,
                                "relation": "unclassified",
                                "requirement_artifact_id": (
                                    record.requirement_artifact_id
                                    or record.claim_artifact_id
                                ),
                            }
                        ),
                        requirement_artifact_id=(
                            record.requirement_artifact_id or record.claim_artifact_id
                        ),
                        claim_artifact_id=(
                            record.effective_target_claim_artifact_ids[0]
                            if record.effective_target_claim_artifact_ids
                            else None
                        ),
                        evidence_artifact_id=evidence_id,
                        relation=(
                            "ambiguous"
                            if "ambigu" in record.outcome
                            else "unclassified"
                        ),
                        rationale=(
                            "candidate was explicitly reported as ambiguous"
                            if "ambigu" in record.outcome
                            else "candidate has no semantic classification record"
                        ),
                        method=(
                            "compatibility_ambiguous"
                            if "ambigu" in record.outcome
                            else "compatibility_unclassified"
                        ),
                        confidence=0.0,
                        material=True,
                        record={},
                    )
                    for evidence_id in record.candidate_evidence_artifact_ids
                )
                for classification in classifications:
                    relation_kind = {
                        "supporting": ObservedEvidenceRelationKind.SUPPORT,
                        "opposing": ObservedEvidenceRelationKind.OPPOSITION,
                        "limiting": ObservedEvidenceRelationKind.LIMITATION,
                        "irrelevant": ObservedEvidenceRelationKind.IRRELEVANCE,
                        "ambiguous": ObservedEvidenceRelationKind.AMBIGUITY,
                        "unclassified": ObservedEvidenceRelationKind.UNCLASSIFIED,
                    }[classification.relation]
                    record_relations = (
                        ()
                        if classification.claim_artifact_id is None
                        else (
                            InstalledEvidenceRelation.create(
                                claim_artifact_id=classification.claim_artifact_id,
                                evidence_artifact_id=classification.evidence_artifact_id,
                                kind=relation_kind,
                                material=classification.material,
                            ),
                        )
                    )
                    relations.extend(record_relations)
                    gap_kind = {
                        ObservedEvidenceRelationKind.OPPOSITION: (
                            ObservedResearchGapKind.MATERIAL_OPPOSITION
                        ),
                        ObservedEvidenceRelationKind.LIMITATION: (
                            ObservedResearchGapKind.MATERIAL_LIMITATION
                        ),
                        ObservedEvidenceRelationKind.AMBIGUITY: (
                            ObservedResearchGapKind.AMBIGUOUS_EVIDENCE
                        ),
                        ObservedEvidenceRelationKind.UNCLASSIFIED: (
                            ObservedResearchGapKind.UNCLASSIFIED_EVIDENCE
                        ),
                    }.get(relation_kind)
                    if classification.material and gap_kind is not None:
                        gaps.append(
                            ObservedResearchGap.create(
                                kind=gap_kind,
                                subject_artifact_id=classification.artifact_id,
                            )
                        )
            requirements = cls._classified_requirements(state, search)
            resolved_requirement_ids = {
                previous.artifact_id
                for previous, current in zip(
                    state.requirements,
                    requirements,
                    strict=True,
                )
                if not previous.satisfied and current.satisfied
            }
            resolved_claim_ids = {
                claim_id
                for previous, current in zip(
                    state.requirements,
                    requirements,
                    strict=True,
                )
                if not previous.satisfied and current.satisfied
                for claim_id in previous.target_claim_artifact_ids
            }
            resolved_insufficiency_relation_ids = {
                relation.artifact_id
                for relation in state.evidence_relations
                if relation.kind is ObservedEvidenceRelationKind.INSUFFICIENCY
                and relation.claim_artifact_id in resolved_claim_ids
            }
            gaps = [
                gap
                for gap in gaps
                if not (
                    gap.kind is ObservedResearchGapKind.UNSATISFIED_REQUIREMENT
                    and gap.subject_artifact_id
                    in resolved_requirement_ids | resolved_insufficiency_relation_ids
                )
            ]
            state = cls._record_decision(
                events,
                state_machine=state_machine,
                state=state,
                state_history=state_history,
                role="skeptic",
                operation="inspect_material_counterevidence",
                rationale=(
                    "classify every material candidate against the exact claim and scope"
                ),
                observation_ids=(search.artifact_id,),
                evidence_ids=candidates,
                policy_ids=policy_ids,
                evidence_relations=tuple(relations),
                requirements=requirements,
                gaps=tuple(gaps),
            )
            unclassified = any(
                classification.relation in {"ambiguous", "unclassified"}
                and classification.material
                for record in search.records
                for classification in record.classifications
            ) or any(not record.classifications for record in search.records)
            return cls._record_decision(
                events,
                state_machine=state_machine,
                state=state,
                state_history=state_history,
                role="adjudicator",
                operation=(
                    "retain_unclassified_material_evidence"
                    if unclassified
                    else "retain_adjudicated_material_evidence"
                ),
                rationale=(
                    "do not complete while a material candidate lacks a resolved relation"
                    if unclassified
                    else "retain classified candidate relations for claim-graph revision"
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
    def _classified_requirements(
        state: ObservedResearchState,
        search: InstalledResearchSearch,
    ) -> tuple[InstalledResearchRequirement, ...]:
        resolved_ids = {
            record.requirement_artifact_id
            for record in search.records
            if record.requirement_artifact_id is not None
            and record.classifications
            and all(
                item.relation not in {"ambiguous", "unclassified"}
                for item in record.classifications
            )
        }
        classification_ids = {
            record.requirement_artifact_id: tuple(
                item.artifact_id for item in record.classifications
            )
            for record in search.records
            if record.requirement_artifact_id is not None
        }
        return tuple(
            requirement
            if requirement.artifact_id not in resolved_ids
            else InstalledResearchRequirement.create(
                description=requirement.description,
                claim_artifact_id=requirement.claim_artifact_id,
                satisfied=True,
                kind=requirement.kind,
                status="satisfied",
                priority=requirement.priority,
                material=requirement.material,
                target_claim_artifact_ids=requirement.target_claim_artifact_ids,
                dependency_requirement_artifact_ids=(
                    requirement.dependency_requirement_artifact_ids
                ),
                satisfaction_criteria=requirement.satisfaction_criteria,
                query_text=None,
                evidence_artifact_ids=tuple(
                    dict.fromkeys(
                        requirement.evidence_artifact_ids
                        + classification_ids.get(requirement.artifact_id, ())
                    )
                ),
                source_gap_artifact_ids=requirement.source_gap_artifact_ids,
                source_requirement_artifact_id=(
                    requirement.source_requirement_artifact_id
                ),
            )
            for requirement in state.requirements
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
            gap.kind is ObservedResearchGapKind.AMBIGUOUS_EVIDENCE for gap in state.gaps
        ):
            return "ambiguous"
        if any(
            gap.kind is ObservedResearchGapKind.RETRIEVAL_REFUSED for gap in state.gaps
        ):
            return "retrieval-refused"
        if ObservedEvidenceRelationKind.OPPOSITION in kinds:
            return "opposing"
        if ObservedEvidenceRelationKind.LIMITATION in kinds:
            return "limiting"
        if ObservedEvidenceRelationKind.SUPPORT in kinds and search is not None:
            return "supporting"
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
        unresolved_candidates = search is not None and any(
            not record.classifications
            or any(
                item.material and item.relation in {"ambiguous", "unclassified"}
                for item in record.classifications
            )
            for record in search.records
            if record.candidate_evidence_artifact_ids
        )
        if candidates and unresolved_candidates:
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
            ObservedResearchGapKind.MATERIAL_LIMITATION: (
                "A material limitation requires answer revision."
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
    "InstalledCandidateClassification",
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
