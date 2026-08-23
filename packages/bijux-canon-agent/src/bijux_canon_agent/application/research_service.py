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

    def __post_init__(self) -> None:
        for value, field in (
            (self.claim_graph_artifact_id, "claim graph artifact_id"),
            (self.scope_artifact_id, "scope artifact_id"),
            (self.counterevidence_policy_artifact_id, "counterevidence policy"),
            (self.convergence_policy_artifact_id, "convergence policy"),
        ):
            _require_artifact_id(value, field)
        if self.verified_claim_count < 0:
            raise ValueError("verified claim count must not be negative")


@dataclass(frozen=True, slots=True)
class InstalledResearchPlan:
    """Counterevidence plan returned by the injected reasoning port."""

    artifact_id: str
    request_artifact_ids: tuple[str, ...]
    record: Mapping[str, object]

    def __post_init__(self) -> None:
        _require_artifact_id(self.artifact_id, "research plan artifact_id")
        for artifact_id in self.request_artifact_ids:
            _require_artifact_id(artifact_id, "research request artifact_id")
        if not isinstance(self.record, Mapping):
            raise TypeError("research plan record must be a mapping")


@dataclass(frozen=True, slots=True)
class InstalledResearchSearchRecord:
    """One material result of a skeptical retrieval request."""

    claim_artifact_id: str
    outcome: str
    candidate_evidence_artifact_ids: tuple[str, ...]
    negative_search_statement: str | None
    record: Mapping[str, object]

    def __post_init__(self) -> None:
        _require_artifact_id(self.claim_artifact_id, "searched claim artifact_id")
        if not self.outcome:
            raise ValueError("research search outcome must not be empty")
        for artifact_id in self.candidate_evidence_artifact_ids:
            _require_artifact_id(artifact_id, "candidate evidence artifact_id")
        if not isinstance(self.record, Mapping):
            raise TypeError("research search record must be a mapping")


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

    def plan(self, request: InstalledResearchRequest) -> InstalledResearchPlan: ...

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
        state = request.claim_graph_artifact_id
        policy_ids = (
            request.counterevidence_policy_artifact_id,
            request.convergence_policy_artifact_id,
        )
        plan = port.plan(request)
        if not isinstance(plan, InstalledResearchPlan):
            raise TypeError("installed research port returned an invalid plan")
        state = self._record_event(
            events,
            state_before=state,
            role="plan",
            operation="plan_counterevidence",
            rationale="select important atomic claims for deliberate skeptical search",
            observation_ids=(plan.artifact_id,),
            evidence_ids=(),
            policy_ids=policy_ids,
        )
        search: InstalledResearchSearch | None = None
        if plan.request_artifact_ids:
            search = port.search(request, plan)
            if not isinstance(search, InstalledResearchSearch):
                raise TypeError("installed research port returned an invalid search")
            candidates = tuple(
                artifact_id
                for record in search.records
                for artifact_id in record.candidate_evidence_artifact_ids
            )
            state = self._record_event(
                events,
                state_before=state,
                role="skeptic",
                operation="search_counterevidence",
                rationale=(
                    "inspect material skeptical retrieval results"
                    if candidates
                    else "retain the bounded negative-search result"
                ),
                observation_ids=(search.artifact_id,),
                evidence_ids=candidates,
                policy_ids=policy_ids,
            )
        else:
            candidates = ()

        relation_status = (
            "unclassified" if candidates else "no-new-counterevidence"
        )
        analysis_id = _artifact_id(
            {
                "candidate_evidence_artifact_ids": candidates,
                "relation": relation_status,
                "search_artifact_id": None if search is None else search.artifact_id,
            }
        )
        state = self._record_event(
            events,
            state_before=state,
            role="analyze",
            operation="classify_research_gap",
            rationale=(
                "require material candidates to be classified before revision"
                if candidates
                else "record that this bounded search found no new counterevidence"
            ),
            observation_ids=(analysis_id,),
            evidence_ids=candidates,
            policy_ids=policy_ids,
        )
        convergence = port.evaluate(request, plan, search)
        if not isinstance(convergence, InstalledResearchConvergence):
            raise TypeError("installed research port returned invalid convergence")
        self._record_event(
            events,
            state_before=state,
            role="terminate",
            operation=(
                "continue_research"
                if not convergence.stop
                else "terminate_research"
            ),
            rationale="apply the declared convergence and resource policy",
            observation_ids=(convergence.artifact_id,),
            evidence_ids=(),
            policy_ids=policy_ids,
            budget_decision_ids=(convergence.artifact_id,),
        )
        insufficiencies = self._insufficiencies(search, candidates)
        causal_events = tuple(events)
        return InstalledResearchResult(
            plan=plan,
            search=search,
            convergence=convergence,
            opposition_candidate_ids=candidates,
            relation_status=relation_status,
            insufficiencies=insufficiencies,
            causal_events=causal_events,
            causal_trace=ResearchCausalTrace.create(causal_events),
        )

    @staticmethod
    def _record_event(
        events: list[CausalDecisionEvent],
        *,
        state_before: str,
        role: str,
        operation: str,
        rationale: str,
        observation_ids: tuple[str, ...],
        evidence_ids: tuple[str, ...],
        policy_ids: tuple[str, ...],
        budget_decision_ids: tuple[str, ...] = (),
    ) -> str:
        sequence = len(events)
        operation_id = observation_ids[0]
        transition_id = _artifact_id(
            {
                "from": state_before,
                "operation": operation,
                "output": operation_id,
                "sequence": sequence,
            }
        )
        state_after = _artifact_id(
            {
                "previous_state_artifact_id": state_before,
                "sequence": sequence,
                "transition_artifact_id": transition_id,
            }
        )
        events.append(
            CausalDecisionEvent.create(
                sequence=sequence,
                state_before_artifact_id=state_before,
                role=role,
                operation=operation,
                rationale=rationale,
                observation_artifact_ids=observation_ids,
                evidence_artifact_ids=evidence_ids,
                tool_decision_artifact_ids=(),
                budget_decision_artifact_ids=budget_decision_ids,
                policy_artifact_ids=policy_ids,
                output_artifact_ids=observation_ids,
                operation_artifact_id=operation_id,
                transition_artifact_id=transition_id,
                state_after_artifact_id=state_after,
            )
        )
        return state_after

    @staticmethod
    def _insufficiencies(
        search: InstalledResearchSearch | None,
        candidates: tuple[str, ...],
    ) -> tuple[str, ...]:
        if search is None:
            return ("No important claim produced a counterevidence request.",)
        findings = tuple(
            record.negative_search_statement
            for record in search.records
            if record.negative_search_statement is not None
        )
        if candidates:
            findings += (
                "Counterevidence candidates require relation classification before use.",
            )
        if any(record.outcome == "retrieval_refused" for record in search.records):
            findings += ("One or more skeptical retrievals were refused.",)
        return findings


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
