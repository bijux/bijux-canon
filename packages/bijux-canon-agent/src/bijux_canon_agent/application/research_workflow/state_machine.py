"""Legal one-operation transitions for a bounded research-agent run."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json
from typing import Any, ClassVar, Protocol, cast, runtime_checkable

from pydantic import TypeAdapter  # type: ignore[attr-defined]

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
class ResearchCheckpoint:
    """Complete durable machine state after one committed transition."""

    artifact_id: str
    sequence: int
    previous_checkpoint_artifact_id: str | None
    planning_input_sha256: str
    tool_policy_artifact_id: str
    budget_policy_artifact_id: str
    retriever_descriptor_sha256: str
    reasoner_descriptor_sha256: str
    role: ResearchRole
    retrieval: RetrievalPortResult | None
    reasoning: ReasoningPortResult | None
    operations: tuple[ResearchOperationRecord, ...]
    transitions: tuple[ResearchTransition, ...]
    tool_decisions: tuple[ToolPolicyDecision, ...]
    budget_decisions: tuple[BudgetDecision, ...]
    cancellation_lineage: tuple[str, ...]
    failure_lineage: tuple[str, ...]

    def to_payload(self) -> dict[str, Any]:
        """Serialize the complete typed checkpoint as canonical JSON values."""
        return cast(
            dict[str, Any],
            TypeAdapter(ResearchCheckpoint).dump_python(self, mode="json"),
        )

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> ResearchCheckpoint:
        """Restore a typed checkpoint and reject ignored or transformed fields."""
        restored = cast(
            ResearchCheckpoint,
            TypeAdapter(cls).validate_python(dict(payload)),
        )
        if restored.to_payload() != dict(payload):
            raise ValueError("checkpoint payload is not exact canonical state")
        return restored


@runtime_checkable
class ResearchCheckpointPort(Protocol):
    """Runtime-owned durable storage used by the Agent state machine."""

    def persist(self, checkpoint: ResearchCheckpoint) -> None: ...

    def load(self, artifact_id: str) -> ResearchCheckpoint: ...


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
    checkpoint_artifact_id: str
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
        checkpoint_port: ResearchCheckpointPort,
        cancellation_lineage: tuple[str, ...] = (),
        failure_lineage: tuple[str, ...] = (),
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
        if not isinstance(checkpoint_port, ResearchCheckpointPort):
            raise TypeError("checkpoint_port must implement ResearchCheckpointPort")
        self._checkpoint_port = checkpoint_port
        self._cancellation_lineage = cancellation_lineage
        self._failure_lineage = failure_lineage
        self._checkpoint: ResearchCheckpoint | None = None
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

    @property
    def checkpoint(self) -> ResearchCheckpoint | None:
        """Return the last state known to have been persisted."""
        return self._checkpoint

    @classmethod
    def resume(
        cls,
        *,
        checkpoint_artifact_id: str,
        planning_input: ResearchPlanningInput,
        services: InjectedResearchServices,
        tool_policy: ToolPolicy,
        budget_policy: ResearchBudgetPolicy,
        checkpoint_port: ResearchCheckpointPort,
    ) -> ResearchRoleMachine:
        """Restore a validated checkpoint without repeating completed tools."""
        checkpoint = checkpoint_port.load(checkpoint_artifact_id)
        machine = cls(
            planning_input=planning_input,
            services=services,
            tool_policy=tool_policy,
            budget_policy=budget_policy,
            checkpoint_port=checkpoint_port,
            cancellation_lineage=checkpoint.cancellation_lineage,
            failure_lineage=checkpoint.failure_lineage,
        )
        machine._validate_checkpoint(checkpoint)
        machine._role = checkpoint.role
        machine._retrieval = checkpoint.retrieval
        machine._reasoning = checkpoint.reasoning
        machine._operations = list(checkpoint.operations)
        machine._transitions = list(checkpoint.transitions)
        machine._services.restore(checkpoint.tool_decisions)
        machine._budget.restore(checkpoint.budget_decisions)
        machine._checkpoint = checkpoint
        return machine

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
        checkpoint = self._create_checkpoint()
        self._checkpoint_port.persist(checkpoint)
        self._checkpoint = checkpoint
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
            "checkpoint_artifact_id": (
                None if self._checkpoint is None else self._checkpoint.artifact_id
            ),
            "terminal_outcome": terminal_outcome,
        }
        if self._checkpoint is None:
            raise RuntimeError("terminal research execution was not checkpointed")
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
            checkpoint_artifact_id=self._checkpoint.artifact_id,
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

    def _create_checkpoint(self) -> ResearchCheckpoint:
        payload = self._checkpoint_payload(
            previous_checkpoint_artifact_id=(
                None if self._checkpoint is None else self._checkpoint.artifact_id
            )
        )
        return ResearchCheckpoint(
            artifact_id=_artifact_id(payload),
            sequence=len(self._transitions) - 1,
            previous_checkpoint_artifact_id=payload[
                "previous_checkpoint_artifact_id"
            ],
            planning_input_sha256=payload["planning_input_sha256"],
            tool_policy_artifact_id=self._services.policy.artifact_id,
            budget_policy_artifact_id=self._budget.policy.artifact_id,
            retriever_descriptor_sha256=payload["retriever_descriptor_sha256"],
            reasoner_descriptor_sha256=payload["reasoner_descriptor_sha256"],
            role=self._role,
            retrieval=self._retrieval,
            reasoning=self._reasoning,
            operations=tuple(self._operations),
            transitions=tuple(self._transitions),
            tool_decisions=self._services.decisions,
            budget_decisions=self._budget.decisions,
            cancellation_lineage=self._cancellation_lineage,
            failure_lineage=self._failure_lineage,
        )

    def _checkpoint_payload(
        self, *, previous_checkpoint_artifact_id: str | None
    ) -> dict[str, Any]:
        return {
            "sequence": len(self._transitions) - 1,
            "previous_checkpoint_artifact_id": previous_checkpoint_artifact_id,
            "planning_input_sha256": hashlib.sha256(
                _canonical(self._planning_input.model_dump(mode="json"))
            ).hexdigest(),
            "tool_policy_artifact_id": self._services.policy.artifact_id,
            "budget_policy_artifact_id": self._budget.policy.artifact_id,
            "retriever_descriptor_sha256": hashlib.sha256(
                _canonical(
                    self._services.retriever_descriptor.model_dump(mode="json")
                )
            ).hexdigest(),
            "reasoner_descriptor_sha256": hashlib.sha256(
                _canonical(
                    self._services.reasoner_descriptor.model_dump(mode="json")
                )
            ).hexdigest(),
            "role": self._role.value,
            "retrieval": (
                None
                if self._retrieval is None
                else self._retrieval.model_dump(mode="json")
            ),
            "reasoning": (
                None
                if self._reasoning is None
                else self._reasoning.model_dump(mode="json")
            ),
            "operation_artifact_ids": [item.artifact_id for item in self._operations],
            "transition_artifact_ids": [
                item.artifact_id for item in self._transitions
            ],
            "tool_decision_artifact_ids": [
                item.artifact_id for item in self._services.decisions
            ],
            "budget_decision_artifact_ids": [
                item.artifact_id for item in self._budget.decisions
            ],
            "cancellation_lineage": list(self._cancellation_lineage),
            "failure_lineage": list(self._failure_lineage),
        }

    def _validate_checkpoint(self, checkpoint: ResearchCheckpoint) -> None:
        if not isinstance(checkpoint, ResearchCheckpoint):
            raise TypeError("checkpoint port returned an invalid checkpoint")
        if checkpoint.sequence != len(checkpoint.transitions) - 1:
            raise ValueError("checkpoint sequence does not match transitions")
        if len(checkpoint.operations) != len(checkpoint.transitions):
            raise ValueError("checkpoint operation and transition counts differ")
        if checkpoint.transitions and checkpoint.transitions[-1].to_role is not checkpoint.role:
            raise ValueError("checkpoint role does not match the transition head")
        for sequence, (operation, transition) in enumerate(
            zip(checkpoint.operations, checkpoint.transitions, strict=True)
        ):
            if operation.sequence != sequence or transition.sequence != sequence:
                raise ValueError("checkpoint execution sequence is not contiguous")
            if operation != ResearchOperationRecord.create(
                sequence=operation.sequence,
                role=operation.role,
                operation=operation.operation,
                input_artifact_ids=operation.input_artifact_ids,
                payload=operation.payload,
            ):
                raise ValueError("checkpoint operation identity is invalid")
            if transition != ResearchTransition.create(
                sequence=transition.sequence,
                from_role=transition.from_role,
                to_role=transition.to_role,
                operation_artifact_id=transition.operation_artifact_id,
            ):
                raise ValueError("checkpoint transition identity is invalid")
            self.validate_transition(
                from_role=transition.from_role,
                to_role=transition.to_role,
                operation=operation.operation,
            )
            if transition.operation_artifact_id != operation.artifact_id:
                raise ValueError("checkpoint transition is not bound to its operation")
        lineage = checkpoint.cancellation_lineage + checkpoint.failure_lineage
        if any(
            len(item) != 71
            or not item.startswith("sha256:")
            or any(char not in "0123456789abcdef" for char in item[7:])
            for item in lineage
        ):
            raise ValueError("checkpoint lineage contains an invalid artifact ID")
        if checkpoint.artifact_id != _artifact_id(
            {
                "sequence": checkpoint.sequence,
                "previous_checkpoint_artifact_id": (
                    checkpoint.previous_checkpoint_artifact_id
                ),
                "planning_input_sha256": checkpoint.planning_input_sha256,
                "tool_policy_artifact_id": checkpoint.tool_policy_artifact_id,
                "budget_policy_artifact_id": checkpoint.budget_policy_artifact_id,
                "retriever_descriptor_sha256": (
                    checkpoint.retriever_descriptor_sha256
                ),
                "reasoner_descriptor_sha256": checkpoint.reasoner_descriptor_sha256,
                "role": checkpoint.role.value,
                "retrieval": (
                    None
                    if checkpoint.retrieval is None
                    else checkpoint.retrieval.model_dump(mode="json")
                ),
                "reasoning": (
                    None
                    if checkpoint.reasoning is None
                    else checkpoint.reasoning.model_dump(mode="json")
                ),
                "operation_artifact_ids": [
                    item.artifact_id for item in checkpoint.operations
                ],
                "transition_artifact_ids": [
                    item.artifact_id for item in checkpoint.transitions
                ],
                "tool_decision_artifact_ids": [
                    item.artifact_id for item in checkpoint.tool_decisions
                ],
                "budget_decision_artifact_ids": [
                    item.artifact_id for item in checkpoint.budget_decisions
                ],
                "cancellation_lineage": list(checkpoint.cancellation_lineage),
                "failure_lineage": list(checkpoint.failure_lineage),
            }
        ):
            raise ValueError("checkpoint content identity is invalid")
        current = self._checkpoint_payload(
            previous_checkpoint_artifact_id=(
                checkpoint.previous_checkpoint_artifact_id
            )
        )
        for field in (
            "planning_input_sha256",
            "tool_policy_artifact_id",
            "budget_policy_artifact_id",
            "retriever_descriptor_sha256",
            "reasoner_descriptor_sha256",
        ):
            if current[field] != getattr(checkpoint, field):
                raise ValueError(f"checkpoint dependency mismatch: {field}")


__all__ = [
    "ResearchExecutionResult",
    "ResearchCheckpoint",
    "ResearchCheckpointPort",
    "ResearchOperation",
    "ResearchOperationRecord",
    "ResearchRole",
    "ResearchRoleMachine",
    "ResearchTransition",
]
