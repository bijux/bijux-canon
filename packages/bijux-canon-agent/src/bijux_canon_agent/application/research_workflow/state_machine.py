"""Legal one-operation transitions for a bounded research-agent run."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json
from typing import Any, ClassVar

from bijux_canon_agent.application.research_services import InjectedResearchServices
from bijux_canon_agent.application.research_tool_gateway import (
    PolicyEnforcedResearchServices,
)
from bijux_canon_agent.contracts.execution_plan import ResearchPlanningInput
from bijux_canon_agent.contracts.research_ports import (
    ReasoningPortResult,
    RetrievalPortResult,
)
from bijux_canon_agent.contracts.research_budget import (
    BudgetAction,
    BudgetDecision,
    BudgetDimensions,
    ResearchBudgetLedger,
    ResearchBudgetPolicy,
)
from bijux_canon_agent.contracts.tool_policy import ToolPolicy, ToolPolicyDecision


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


class ResearchRole(StrEnum):
    """Ordered roles in one bounded research execution."""

    PLAN = "plan"
    RETRIEVE = "retrieve"
    ANALYZE = "analyze"
    SKEPTIC = "skeptic"
    GAP_FILL = "gap_fill"
    SYNTHESIZE = "synthesize"
    VERIFY = "verify"
    TERMINATE = "terminate"
    TERMINAL = "terminal"


class ResearchOperation(StrEnum):
    """Exactly one operation owned by each research role."""

    VALIDATE_PLAN = "validate_plan"
    RETRIEVE_EVIDENCE = "retrieve_evidence"
    ANALYZE_EVIDENCE = "analyze_evidence"
    ASSESS_COUNTEREVIDENCE = "assess_counterevidence"
    RESOLVE_EVIDENCE_GAPS = "resolve_evidence_gaps"
    SYNTHESIZE_ANSWER = "synthesize_answer"
    VERIFY_ANSWER = "verify_answer"
    TERMINATE_RUN = "terminate_run"


@dataclass(frozen=True, slots=True)
class ResearchOperationRecord:
    """Content-addressed result of one declared state-machine operation."""

    artifact_id: str
    sequence: int
    role: ResearchRole
    operation: ResearchOperation
    input_artifact_ids: tuple[str, ...]
    payload: Mapping[str, Any]

    @classmethod
    def create(
        cls,
        *,
        sequence: int,
        role: ResearchRole,
        operation: ResearchOperation,
        input_artifact_ids: tuple[str, ...],
        payload: Mapping[str, Any],
    ) -> ResearchOperationRecord:
        canonical_payload = {
            "sequence": sequence,
            "role": role.value,
            "operation": operation.value,
            "input_artifact_ids": list(input_artifact_ids),
            "payload": dict(payload),
        }
        return cls(
            artifact_id=_artifact_id(canonical_payload),
            sequence=sequence,
            role=role,
            operation=operation,
            input_artifact_ids=input_artifact_ids,
            payload=dict(payload),
        )


@dataclass(frozen=True, slots=True)
class ResearchTransition:
    """A validated role edge caused by exactly one operation record."""

    artifact_id: str
    sequence: int
    from_role: ResearchRole
    to_role: ResearchRole
    operation_artifact_id: str

    @classmethod
    def create(
        cls,
        *,
        sequence: int,
        from_role: ResearchRole,
        to_role: ResearchRole,
        operation_artifact_id: str,
    ) -> ResearchTransition:
        payload = {
            "sequence": sequence,
            "from_role": from_role.value,
            "to_role": to_role.value,
            "operation_artifact_id": operation_artifact_id,
        }
        return cls(
            artifact_id=_artifact_id(payload),
            sequence=sequence,
            from_role=from_role,
            to_role=to_role,
            operation_artifact_id=operation_artifact_id,
        )


@dataclass(frozen=True, slots=True)
class ResearchExecutionResult:
    """Terminal immutable state produced by the research role machine."""

    artifact_id: str
    planning_input: ResearchPlanningInput
    retrieval: RetrievalPortResult | None
    reasoning: ReasoningPortResult | None
    operations: tuple[ResearchOperationRecord, ...]
    transitions: tuple[ResearchTransition, ...]
    tool_policy_artifact_id: str
    tool_decisions: tuple[ToolPolicyDecision, ...]
    budget_policy_artifact_id: str
    budget_decisions: tuple[BudgetDecision, ...]
    budget_usage: BudgetDimensions
    exhausted_budget_dimensions: tuple[str, ...]
    terminal_outcome: str


class ResearchRoleMachine:
    """Execute the fixed legal research-role sequence through injected ports."""

    MAX_TRANSITIONS: ClassVar[int] = 8
    _NEXT_ROLE: ClassVar[dict[ResearchRole, ResearchRole]] = {
        ResearchRole.PLAN: ResearchRole.RETRIEVE,
        ResearchRole.RETRIEVE: ResearchRole.ANALYZE,
        ResearchRole.ANALYZE: ResearchRole.SKEPTIC,
        ResearchRole.SKEPTIC: ResearchRole.GAP_FILL,
        ResearchRole.GAP_FILL: ResearchRole.SYNTHESIZE,
        ResearchRole.SYNTHESIZE: ResearchRole.VERIFY,
        ResearchRole.VERIFY: ResearchRole.TERMINATE,
        ResearchRole.TERMINATE: ResearchRole.TERMINAL,
    }
    _OPERATION: ClassVar[dict[ResearchRole, ResearchOperation]] = {
        ResearchRole.PLAN: ResearchOperation.VALIDATE_PLAN,
        ResearchRole.RETRIEVE: ResearchOperation.RETRIEVE_EVIDENCE,
        ResearchRole.ANALYZE: ResearchOperation.ANALYZE_EVIDENCE,
        ResearchRole.SKEPTIC: ResearchOperation.ASSESS_COUNTEREVIDENCE,
        ResearchRole.GAP_FILL: ResearchOperation.RESOLVE_EVIDENCE_GAPS,
        ResearchRole.SYNTHESIZE: ResearchOperation.SYNTHESIZE_ANSWER,
        ResearchRole.VERIFY: ResearchOperation.VERIFY_ANSWER,
        ResearchRole.TERMINATE: ResearchOperation.TERMINATE_RUN,
    }

    def __init__(
        self,
        *,
        planning_input: ResearchPlanningInput,
        services: InjectedResearchServices,
        tool_policy: ToolPolicy,
        budget_policy: ResearchBudgetPolicy,
    ) -> None:
        self._planning_input = planning_input
        self._services = PolicyEnforcedResearchServices(
            planning_input=planning_input,
            services=services,
            policy=tool_policy,
        )
        if budget_policy.plan_sha256 != tool_policy.plan_sha256:
            raise ValueError("budget policy is not bound to the research plan")
        self._budget = ResearchBudgetLedger(budget_policy)
        self._role = ResearchRole.PLAN
        self._retrieval: RetrievalPortResult | None = None
        self._reasoning: ReasoningPortResult | None = None
        self._operations: list[ResearchOperationRecord] = []
        self._transitions: list[ResearchTransition] = []

    @property
    def role(self) -> ResearchRole:
        """Return the current role without exposing mutable machine state."""
        return self._role

    @property
    def operations(self) -> tuple[ResearchOperationRecord, ...]:
        return tuple(self._operations)

    @property
    def transitions(self) -> tuple[ResearchTransition, ...]:
        return tuple(self._transitions)

    @property
    def tool_decisions(self) -> tuple[ToolPolicyDecision, ...]:
        """Return policy decisions, including a denial that halted execution."""
        return self._services.decisions

    @property
    def budget_decisions(self) -> tuple[BudgetDecision, ...]:
        """Return every global and per-role accounting decision."""
        return self._budget.decisions

    @classmethod
    def validate_transition(
        cls,
        *,
        from_role: ResearchRole,
        to_role: ResearchRole,
        operation: ResearchOperation,
    ) -> None:
        """Reject skipped roles, reverse edges, and role-operation mismatches."""
        if cls._NEXT_ROLE.get(from_role) is not to_role:
            raise ValueError(
                f"illegal research transition {from_role.value} -> {to_role.value}"
            )
        if cls._OPERATION.get(from_role) is not operation:
            raise ValueError(
                f"operation {operation.value} is not owned by role {from_role.value}"
            )

    def advance(self) -> ResearchTransition:
        """Execute one operation and advance exactly one legal role edge."""
        if self._role is ResearchRole.TERMINAL:
            raise RuntimeError("terminal research execution cannot advance")
        if len(self._transitions) >= self.MAX_TRANSITIONS:
            raise RuntimeError("research transition bound exceeded")
        from_role = self._role
        to_role = self._NEXT_ROLE[from_role]
        operation = self._OPERATION[from_role]
        self.validate_transition(
            from_role=from_role,
            to_role=to_role,
            operation=operation,
        )
        record = self._execute_operation(operation)
        transition = ResearchTransition.create(
            sequence=len(self._transitions),
            from_role=from_role,
            to_role=to_role,
            operation_artifact_id=record.artifact_id,
        )
        self._operations.append(record)
        self._transitions.append(transition)
        self._role = to_role
        return transition

    def run(self) -> ResearchExecutionResult:
        """Run the complete bounded sequence and return immutable terminal state."""
        while self._role is not ResearchRole.TERMINAL:
            self.advance()
        if self._budget.exhausted_dimensions:
            terminal_outcome = "budget_exhausted:" + ",".join(
                self._budget.exhausted_dimensions
            )
        elif self._retrieval is None or self._reasoning is None:
            terminal_outcome = "incomplete"
        else:
            terminal_outcome = self._reasoning.outcome
        payload = {
            "planning_input": self._planning_input.model_dump(mode="json"),
            "retrieval_artifact_id": (
                None if self._retrieval is None else self._retrieval.artifact_id
            ),
            "reasoning_artifact_id": (
                None if self._reasoning is None else self._reasoning.artifact_id
            ),
            "operation_artifact_ids": [item.artifact_id for item in self._operations],
            "transition_artifact_ids": [
                item.artifact_id for item in self._transitions
            ],
            "tool_policy_artifact_id": self._services.policy.artifact_id,
            "tool_decision_artifact_ids": [
                item.artifact_id for item in self._services.decisions
            ],
            "budget_policy_artifact_id": self._budget.policy.artifact_id,
            "budget_decision_artifact_ids": [
                item.artifact_id for item in self._budget.decisions
            ],
            "budget_usage": self._budget.global_usage.payload(),
            "exhausted_budget_dimensions": list(
                self._budget.exhausted_dimensions
            ),
            "terminal_outcome": terminal_outcome,
        }
        return ResearchExecutionResult(
            artifact_id=_artifact_id(payload),
            planning_input=self._planning_input,
            retrieval=self._retrieval,
            reasoning=self._reasoning,
            operations=tuple(self._operations),
            transitions=tuple(self._transitions),
            tool_policy_artifact_id=self._services.policy.artifact_id,
            tool_decisions=self._services.decisions,
            budget_policy_artifact_id=self._budget.policy.artifact_id,
            budget_decisions=self._budget.decisions,
            budget_usage=self._budget.global_usage,
            exhausted_budget_dimensions=self._budget.exhausted_dimensions,
            terminal_outcome=terminal_outcome,
        )

    def _execute_operation(
        self, operation: ResearchOperation
    ) -> ResearchOperationRecord:
        sequence = len(self._operations)
        inputs = self._operation_inputs()
        role = self._role.value
        start_charge = BudgetDimensions(
            iterations=1,
            retrievals=int(operation is ResearchOperation.RETRIEVE_EVIDENCE),
            tool_calls=int(operation is ResearchOperation.RETRIEVE_EVIDENCE),
            provider_calls=int(operation is ResearchOperation.SYNTHESIZE_ANSWER),
            elapsed_ms=1,
        )
        start_decision = self._budget.charge(
            role=role,
            label=f"{operation.value}:start",
            usage=start_charge,
        )
        if start_decision.action is BudgetAction.TERMINATE:
            return ResearchOperationRecord.create(
                sequence=sequence,
                role=self._role,
                operation=operation,
                input_artifact_ids=inputs,
                payload={
                    "budget_decision_artifact_id": start_decision.artifact_id,
                    "status": "budget_exhausted",
                    "exhausted_dimensions": list(
                        start_decision.exhausted_dimensions
                    ),
                },
            )
        if operation is ResearchOperation.VALIDATE_PLAN:
            payload: Mapping[str, Any] = {
                "planning_input_sha256": hashlib.sha256(
                    _canonical(self._planning_input.model_dump(mode="json"))
                ).hexdigest(),
                "step_count": self.MAX_TRANSITIONS,
            }
        elif operation is ResearchOperation.RETRIEVE_EVIDENCE:
            self._retrieval = self._services.retrieve()
            payload = {
                "retrieval_artifact_id": self._retrieval.artifact_id,
                "record_count": len(self._retrieval.records),
                "tool_policy_decision_artifact_id": (
                    self._services.decisions[-1].artifact_id
                ),
            }
        elif operation is ResearchOperation.ANALYZE_EVIDENCE:
            retrieval = self._require_retrieval()
            payload = {
                "retrieval_artifact_id": retrieval.artifact_id,
                "observed_record_count": len(retrieval.records),
                "has_evidence": bool(retrieval.records),
            }
        elif operation is ResearchOperation.ASSESS_COUNTEREVIDENCE:
            retrieval = self._require_retrieval()
            payload = {
                "retrieval_artifact_id": retrieval.artifact_id,
                "assessment": (
                    "inspect_for_opposition" if retrieval.records else "evidence_missing"
                ),
            }
        elif operation is ResearchOperation.RESOLVE_EVIDENCE_GAPS:
            retrieval = self._require_retrieval()
            payload = {
                "retrieval_artifact_id": retrieval.artifact_id,
                "gap_status": "bounded" if retrieval.records else "insufficient",
                "remaining_gap_count": 0 if retrieval.records else 1,
            }
        elif operation is ResearchOperation.SYNTHESIZE_ANSWER:
            self._reasoning = self._services.reason(self._require_retrieval())
            payload = {
                "reasoning_artifact_id": self._reasoning.artifact_id,
                "outcome": self._reasoning.outcome,
                "tool_policy_decision_artifact_id": (
                    self._services.decisions[-1].artifact_id
                ),
            }
        elif operation is ResearchOperation.VERIFY_ANSWER:
            reasoning = self._require_reasoning()
            payload = {
                "reasoning_artifact_id": reasoning.artifact_id,
                "request_bound": True,
                "artifact_identity_valid": reasoning.artifact_id.startswith("sha256:"),
            }
        else:
            terminal_reasoning = self._reasoning
            payload = {
                "reasoning_artifact_id": (
                    None
                    if terminal_reasoning is None
                    else terminal_reasoning.artifact_id
                ),
                "terminal_outcome": (
                    "budget_exhausted"
                    if terminal_reasoning is None
                    else terminal_reasoning.outcome
                ),
            }
        payload = {"budget_decision_artifact_id": start_decision.artifact_id, **payload}
        output_bytes = len(_canonical(payload))
        if (
            operation is ResearchOperation.RETRIEVE_EVIDENCE
            and self._retrieval is not None
        ):
            output_bytes += len(
                _canonical(self._retrieval.model_dump(mode="json"))
            )
        if (
            operation is ResearchOperation.SYNTHESIZE_ANSWER
            and self._reasoning is not None
        ):
            output_bytes += len(_canonical(self._reasoning.model_dump(mode="json")))
        dynamic_charge = BudgetDimensions(
            candidates=(
                len(self._retrieval.records)
                if operation is ResearchOperation.RETRIEVE_EVIDENCE
                and self._retrieval is not None
                else 0
            ),
            evidence_items=(
                len(self._retrieval.records)
                if operation is ResearchOperation.RETRIEVE_EVIDENCE
                and self._retrieval is not None
                else 0
            ),
            tokens=(
                len((self._reasoning.text or "").split())
                if operation is ResearchOperation.SYNTHESIZE_ANSWER
                and self._reasoning is not None
                else 0
            ),
            artifact_bytes=output_bytes,
        )
        finish_decision = self._budget.charge(
            role=role,
            label=f"{operation.value}:finish",
            usage=dynamic_charge,
        )
        payload = {
            **payload,
            "budget_finish_decision_artifact_id": finish_decision.artifact_id,
        }
        return ResearchOperationRecord.create(
            sequence=sequence,
            role=self._role,
            operation=operation,
            input_artifact_ids=inputs,
            payload=payload,
        )

    def _operation_inputs(self) -> tuple[str, ...]:
        if not self._operations:
            return ()
        return (self._operations[-1].artifact_id,)

    def _require_retrieval(self) -> RetrievalPortResult:
        if self._retrieval is None:
            raise RuntimeError("research operation requires retrieval output")
        return self._retrieval

    def _require_reasoning(self) -> ReasoningPortResult:
        if self._reasoning is None:
            raise RuntimeError("research operation requires reasoning output")
        return self._reasoning


__all__ = [
    "ResearchExecutionResult",
    "ResearchOperation",
    "ResearchOperationRecord",
    "ResearchRole",
    "ResearchRoleMachine",
    "ResearchTransition",
]
