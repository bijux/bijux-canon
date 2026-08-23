"""Legal one-operation transitions for a bounded research-agent run."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json
from typing import Any, ClassVar, Protocol, cast, runtime_checkable

from pydantic import TypeAdapter

from bijux_canon_agent.application.research_services import InjectedResearchServices
from bijux_canon_agent.application.research_tool_gateway import (
    PolicyEnforcedResearchServices,
    ToolPolicyDenied,
)
from bijux_canon_agent.contracts.causal_trace import (
    CausalDecisionEvent,
    ResearchCausalTrace,
)
from bijux_canon_agent.contracts.execution_control import (
    CancellationPort,
    CancellationSignal,
    ResearchFailureKind,
    ResearchFailureRecord,
)
from bijux_canon_agent.contracts.execution_plan import ResearchPlanningInput
from bijux_canon_agent.contracts.research_budget import (
    BudgetAction,
    BudgetDecision,
    BudgetDimensions,
    ResearchBudgetLedger,
    ResearchBudgetPolicy,
)
from bijux_canon_agent.contracts.research_ports import (
    ReasoningPortResult,
    RetrievalPortResult,
)
from bijux_canon_agent.contracts.tool_execution import ToolExecutionRecord
from bijux_canon_agent.contracts.tool_policy import (
    ToolPolicy,
    ToolPolicyAction,
    ToolPolicyDecision,
)
from bijux_canon_agent.tooling.registry import ResearchToolCallCancelled


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
    tool_descriptor_artifact_ids: tuple[str, ...]
    tool_decisions: tuple[ToolPolicyDecision, ...]
    tool_execution_records: tuple[ToolExecutionRecord, ...]
    budget_decisions: tuple[BudgetDecision, ...]
    causal_events: tuple[CausalDecisionEvent, ...]
    cancellation_signal: CancellationSignal | None
    failure_records: tuple[ResearchFailureRecord, ...]
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
        restored = TypeAdapter(cls).validate_python(dict(payload))
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
    tool_descriptor_artifact_ids: tuple[str, ...]
    tool_decisions: tuple[ToolPolicyDecision, ...]
    tool_execution_records: tuple[ToolExecutionRecord, ...]
    budget_policy_artifact_id: str
    budget_decisions: tuple[BudgetDecision, ...]
    budget_usage: BudgetDimensions
    exhausted_budget_dimensions: tuple[str, ...]
    checkpoint_artifact_id: str
    causal_events: tuple[CausalDecisionEvent, ...]
    causal_trace: ResearchCausalTrace
    cancellation_signal: CancellationSignal | None
    failure_records: tuple[ResearchFailureRecord, ...]
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
    _RATIONALE: ClassVar[dict[ResearchOperation, str]] = {
        ResearchOperation.VALIDATE_PLAN: "validate exact declared inputs",
        ResearchOperation.RETRIEVE_EVIDENCE: "obtain scoped candidate evidence",
        ResearchOperation.ANALYZE_EVIDENCE: "inspect retrieved observations",
        ResearchOperation.ASSESS_COUNTEREVIDENCE: "test claims against opposition",
        ResearchOperation.RESOLVE_EVIDENCE_GAPS: "classify unresolved evidence needs",
        ResearchOperation.SYNTHESIZE_ANSWER: "produce a bounded evidence synthesis",
        ResearchOperation.VERIFY_ANSWER: "verify request and artifact bindings",
        ResearchOperation.TERMINATE_RUN: "commit the declared terminal outcome",
    }

    def __init__(
        self,
        *,
        planning_input: ResearchPlanningInput,
        services: InjectedResearchServices,
        tool_policy: ToolPolicy,
        budget_policy: ResearchBudgetPolicy,
        checkpoint_port: ResearchCheckpointPort,
        cancellation_port: CancellationPort,
        cancellation_lineage: tuple[str, ...] = (),
        failure_lineage: tuple[str, ...] = (),
    ) -> None:
        self._planning_input = planning_input
        self._services = PolicyEnforcedResearchServices(
            planning_input=planning_input,
            services=services,
            policy=tool_policy,
            cancellation_port=cancellation_port,
        )
        if budget_policy.plan_sha256 != tool_policy.plan_sha256:
            raise ValueError("budget policy is not bound to the research plan")
        self._budget = ResearchBudgetLedger(budget_policy)
        if not isinstance(checkpoint_port, ResearchCheckpointPort):
            raise TypeError("checkpoint_port must implement ResearchCheckpointPort")
        self._checkpoint_port = checkpoint_port
        if not isinstance(cancellation_port, CancellationPort):
            raise TypeError("cancellation_port must implement CancellationPort")
        self._cancellation_port = cancellation_port
        self._cancellation_signal: CancellationSignal | None = None
        self._failure_records: list[ResearchFailureRecord] = []
        self._cancellation_lineage = cancellation_lineage
        self._failure_lineage = failure_lineage
        self._checkpoint: ResearchCheckpoint | None = None
        self._causal_events: list[CausalDecisionEvent] = []
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

    @property
    def causal_events(self) -> tuple[CausalDecisionEvent, ...]:
        """Return the ordered cause-and-effect records built so far."""
        return tuple(self._causal_events)

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
        cancellation_port: CancellationPort,
    ) -> ResearchRoleMachine:
        """Restore a validated checkpoint without repeating completed tools."""
        checkpoint = checkpoint_port.load(checkpoint_artifact_id)
        machine = cls(
            planning_input=planning_input,
            services=services,
            tool_policy=tool_policy,
            budget_policy=budget_policy,
            checkpoint_port=checkpoint_port,
            cancellation_port=cancellation_port,
            cancellation_lineage=checkpoint.cancellation_lineage,
            failure_lineage=checkpoint.failure_lineage,
        )
        machine._validate_checkpoint(checkpoint)
        machine._role = checkpoint.role
        machine._retrieval = checkpoint.retrieval
        machine._reasoning = checkpoint.reasoning
        machine._operations = list(checkpoint.operations)
        machine._transitions = list(checkpoint.transitions)
        machine._services.restore(
            checkpoint.tool_decisions,
            checkpoint.tool_execution_records,
        )
        machine._budget.restore(checkpoint.budget_decisions)
        machine._causal_events = list(checkpoint.causal_events)
        machine._cancellation_signal = checkpoint.cancellation_signal
        machine._failure_records = list(checkpoint.failure_records)
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
        tool_decision_start = len(self._services.decisions)
        budget_decision_start = len(self._budget.decisions)
        self.validate_transition(
            from_role=from_role,
            to_role=to_role,
            operation=operation,
        )
        try:
            record = self._execute_operation(operation)
        except Exception as error:
            signal = self._cancellation_port.current()
            if isinstance(error, ResearchToolCallCancelled) and signal.requested:
                self._cancellation_signal = signal
                self._cancellation_lineage = tuple(
                    dict.fromkeys(self._cancellation_lineage + (signal.artifact_id,))
                )
                record = ResearchOperationRecord.create(
                    sequence=len(self._operations),
                    role=self._role,
                    operation=operation,
                    input_artifact_ids=self._operation_inputs(),
                    payload={
                        "status": "cancelled",
                        "cancellation_artifact_id": signal.artifact_id,
                        "tool_execution_record_artifact_id": (
                            self._services.execution_records[-1].artifact_id
                        ),
                    },
                )
            else:
                failure = self._classify_failure(error, operation)
                self._failure_records.append(failure)
                self._failure_lineage = tuple(
                    dict.fromkeys(self._failure_lineage + (failure.artifact_id,))
                )
                record = ResearchOperationRecord.create(
                    sequence=len(self._operations),
                    role=self._role,
                    operation=operation,
                    input_artifact_ids=self._operation_inputs(),
                    payload={
                        "status": "failed",
                        "failure_artifact_id": failure.artifact_id,
                        "failure_kind": failure.kind.value,
                        "retryable": failure.retryable,
                    },
                )
        transition = ResearchTransition.create(
            sequence=len(self._transitions),
            from_role=from_role,
            to_role=to_role,
            operation_artifact_id=record.artifact_id,
        )
        self._operations.append(record)
        self._transitions.append(transition)
        self._role = to_role
        self._causal_events.append(
            self._create_causal_event(
                record=record,
                transition=transition,
                tool_decision_start=tool_decision_start,
                budget_decision_start=budget_decision_start,
            )
        )
        checkpoint = self._create_checkpoint()
        self._checkpoint_port.persist(checkpoint)
        self._checkpoint = checkpoint
        return transition

    def run(self) -> ResearchExecutionResult:
        """Run the complete bounded sequence and return immutable terminal state."""
        while self._role is not ResearchRole.TERMINAL:
            self.advance()
        if self._cancellation_signal is not None:
            terminal_outcome = "cancelled:" + str(self._cancellation_signal.reason)
        elif self._failure_records:
            terminal_outcome = "failed:" + self._failure_records[-1].kind.value
        elif self._budget.exhausted_dimensions:
            terminal_outcome = "budget_exhausted:" + ",".join(
                self._budget.exhausted_dimensions
            )
        elif self._retrieval is None or self._reasoning is None:
            terminal_outcome = "incomplete"
        else:
            terminal_outcome = self._reasoning.outcome
        causal_trace = ResearchCausalTrace.create(tuple(self._causal_events))
        payload = {
            "planning_input": self._planning_input.model_dump(mode="json"),
            "retrieval_artifact_id": (
                None if self._retrieval is None else self._retrieval.artifact_id
            ),
            "reasoning_artifact_id": (
                None if self._reasoning is None else self._reasoning.artifact_id
            ),
            "operation_artifact_ids": [item.artifact_id for item in self._operations],
            "transition_artifact_ids": [item.artifact_id for item in self._transitions],
            "tool_policy_artifact_id": self._services.policy.artifact_id,
            "tool_descriptor_artifact_ids": [
                item.artifact_id for item in self._services.tool_descriptors
            ],
            "tool_decision_artifact_ids": [
                item.artifact_id for item in self._services.decisions
            ],
            "tool_execution_record_artifact_ids": [
                item.artifact_id for item in self._services.execution_records
            ],
            "budget_policy_artifact_id": self._budget.policy.artifact_id,
            "budget_decision_artifact_ids": [
                item.artifact_id for item in self._budget.decisions
            ],
            "budget_usage": self._budget.global_usage.payload(),
            "exhausted_budget_dimensions": list(self._budget.exhausted_dimensions),
            "checkpoint_artifact_id": (
                None if self._checkpoint is None else self._checkpoint.artifact_id
            ),
            "causal_trace_artifact_id": causal_trace.artifact_id,
            "cancellation_artifact_id": (
                None
                if self._cancellation_signal is None
                else self._cancellation_signal.artifact_id
            ),
            "failure_artifact_ids": [
                item.artifact_id for item in self._failure_records
            ],
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
            tool_descriptor_artifact_ids=tuple(
                item.artifact_id for item in self._services.tool_descriptors
            ),
            tool_decisions=self._services.decisions,
            tool_execution_records=self._services.execution_records,
            budget_policy_artifact_id=self._budget.policy.artifact_id,
            budget_decisions=self._budget.decisions,
            budget_usage=self._budget.global_usage,
            exhausted_budget_dimensions=self._budget.exhausted_dimensions,
            checkpoint_artifact_id=self._checkpoint.artifact_id,
            causal_events=tuple(self._causal_events),
            causal_trace=causal_trace,
            cancellation_signal=self._cancellation_signal,
            failure_records=tuple(self._failure_records),
            terminal_outcome=terminal_outcome,
        )

    def _execute_operation(
        self, operation: ResearchOperation
    ) -> ResearchOperationRecord:
        sequence = len(self._operations)
        inputs = self._operation_inputs()
        if self._cancellation_signal is None and not self._failure_records:
            signal = self._cancellation_port.current()
            if not isinstance(signal, CancellationSignal):
                raise TypeError("cancellation port returned an invalid signal")
            if signal.requested:
                self._cancellation_signal = signal
                self._cancellation_lineage = tuple(
                    dict.fromkeys(self._cancellation_lineage + (signal.artifact_id,))
                )
        if self._cancellation_signal is not None:
            return ResearchOperationRecord.create(
                sequence=sequence,
                role=self._role,
                operation=operation,
                input_artifact_ids=inputs,
                payload={
                    "status": "cancelled",
                    "cancellation_artifact_id": self._cancellation_signal.artifact_id,
                },
            )
        if self._failure_records:
            return ResearchOperationRecord.create(
                sequence=sequence,
                role=self._role,
                operation=operation,
                input_artifact_ids=inputs,
                payload={
                    "status": "failed_dependency",
                    "failure_artifact_id": self._failure_records[-1].artifact_id,
                },
            )
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
                    "exhausted_dimensions": list(start_decision.exhausted_dimensions),
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
            reservation = self._reserve_tool_operation(operation)
            if reservation.action is BudgetAction.TERMINATE:
                return self._budget_exhausted_operation(
                    sequence=sequence,
                    operation=operation,
                    inputs=inputs,
                    decision=reservation,
                    start_decision=start_decision,
                )
            self._retrieval = self._services.retrieve()
            payload = {
                "retrieval_artifact_id": self._retrieval.artifact_id,
                "record_count": len(self._retrieval.records),
                "budget_reservation_artifact_id": reservation.artifact_id,
                "tool_policy_decision_artifact_id": (
                    self._services.decisions[-1].artifact_id
                ),
                "tool_execution_record_artifact_id": (
                    self._services.execution_records[-1].artifact_id
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
                    "inspect_for_opposition"
                    if retrieval.records
                    else "evidence_missing"
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
            reservation = self._reserve_tool_operation(operation)
            if reservation.action is BudgetAction.TERMINATE:
                return self._budget_exhausted_operation(
                    sequence=sequence,
                    operation=operation,
                    inputs=inputs,
                    decision=reservation,
                    start_decision=start_decision,
                )
            self._reasoning = self._services.reason(self._require_retrieval())
            payload = {
                "reasoning_artifact_id": self._reasoning.artifact_id,
                "outcome": self._reasoning.outcome,
                "budget_reservation_artifact_id": reservation.artifact_id,
                "tool_policy_decision_artifact_id": (
                    self._services.decisions[-1].artifact_id
                ),
                "tool_execution_record_artifact_id": (
                    self._services.execution_records[-1].artifact_id
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
            output_bytes += len(_canonical(self._retrieval.model_dump(mode="json")))
        if (
            operation is ResearchOperation.SYNTHESIZE_ANSWER
            and self._reasoning is not None
        ):
            output_bytes += len(_canonical(self._reasoning.model_dump(mode="json")))
        dynamic_charge = BudgetDimensions(
            documents=(
                self._retrieval_document_count(self._retrieval.records)
                if operation is ResearchOperation.RETRIEVE_EVIDENCE
                and self._retrieval is not None
                else 0
            ),
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
            memory_bytes=len(
                _canonical(
                    {
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
                    }
                )
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
        if finish_decision.action is BudgetAction.TERMINATE:
            if operation is ResearchOperation.RETRIEVE_EVIDENCE:
                self._retrieval = None
            elif operation is ResearchOperation.SYNTHESIZE_ANSWER:
                self._reasoning = None
            payload = {
                **payload,
                "status": "budget_exhausted",
                "result_admitted": False,
                "exhausted_dimensions": list(finish_decision.exhausted_dimensions),
            }
        return ResearchOperationRecord.create(
            sequence=sequence,
            role=self._role,
            operation=operation,
            input_artifact_ids=inputs,
            payload=payload,
        )

    def _reserve_tool_operation(
        self, operation: ResearchOperation
    ) -> BudgetDecision:
        role = self._role.value
        capacity = self._budget.remaining(role=role)
        if operation is ResearchOperation.RETRIEVE_EVIDENCE:
            maximum = BudgetDimensions(
                documents=self._planning_input.top_k,
                candidates=self._planning_input.top_k,
                evidence_items=self._planning_input.top_k,
                memory_bytes=capacity.memory_bytes,
                artifact_bytes=capacity.artifact_bytes,
            )
        elif operation is ResearchOperation.SYNTHESIZE_ANSWER:
            maximum = BudgetDimensions(
                tokens=capacity.tokens,
                memory_bytes=capacity.memory_bytes,
                artifact_bytes=capacity.artifact_bytes,
            )
        else:
            raise ValueError("only external tool operations require reservations")
        return self._budget.reserve(
            role=role,
            label=f"{operation.value}:reserve",
            maximum=maximum,
        )

    def _budget_exhausted_operation(
        self,
        *,
        sequence: int,
        operation: ResearchOperation,
        inputs: tuple[str, ...],
        decision: BudgetDecision,
        start_decision: BudgetDecision,
    ) -> ResearchOperationRecord:
        return ResearchOperationRecord.create(
            sequence=sequence,
            role=self._role,
            operation=operation,
            input_artifact_ids=inputs,
            payload={
                "budget_decision_artifact_id": start_decision.artifact_id,
                "budget_reservation_artifact_id": decision.artifact_id,
                "status": "budget_exhausted",
                "result_admitted": False,
                "exhausted_dimensions": list(decision.exhausted_dimensions),
            },
        )

    @staticmethod
    def _retrieval_document_count(records: tuple[Mapping[str, Any], ...]) -> int:
        identities = {
            str(
                record.get("document_id")
                or record.get("source_id")
                or record.get("chunk_id")
                or _artifact_id(record)
            )
            for record in records
        }
        return len(identities)

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
            previous_checkpoint_artifact_id=payload["previous_checkpoint_artifact_id"],
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
            tool_descriptor_artifact_ids=tuple(
                item.artifact_id for item in self._services.tool_descriptors
            ),
            tool_decisions=self._services.decisions,
            tool_execution_records=self._services.execution_records,
            budget_decisions=self._budget.decisions,
            causal_events=tuple(self._causal_events),
            cancellation_signal=self._cancellation_signal,
            failure_records=tuple(self._failure_records),
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
            "tool_descriptor_artifact_ids": [
                item.artifact_id for item in self._services.tool_descriptors
            ],
            "budget_policy_artifact_id": self._budget.policy.artifact_id,
            "retriever_descriptor_sha256": hashlib.sha256(
                _canonical(self._services.retriever_descriptor.model_dump(mode="json"))
            ).hexdigest(),
            "reasoner_descriptor_sha256": hashlib.sha256(
                _canonical(self._services.reasoner_descriptor.model_dump(mode="json"))
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
            "transition_artifact_ids": [item.artifact_id for item in self._transitions],
            "tool_decision_artifact_ids": [
                item.artifact_id for item in self._services.decisions
            ],
            "tool_execution_record_artifact_ids": [
                item.artifact_id for item in self._services.execution_records
            ],
            "budget_decision_artifact_ids": [
                item.artifact_id for item in self._budget.decisions
            ],
            "causal_event_artifact_ids": [
                item.artifact_id for item in self._causal_events
            ],
            "cancellation_artifact_id": (
                None
                if self._cancellation_signal is None
                else self._cancellation_signal.artifact_id
            ),
            "failure_artifact_ids": [
                item.artifact_id for item in self._failure_records
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
        if (
            checkpoint.transitions
            and checkpoint.transitions[-1].to_role is not checkpoint.role
        ):
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
        if len(checkpoint.causal_events) != len(checkpoint.transitions):
            raise ValueError("checkpoint causal event and transition counts differ")
        for sequence, event in enumerate(checkpoint.causal_events):
            if event.sequence != sequence:
                raise ValueError("checkpoint causal events are not contiguous")
            expected_event = CausalDecisionEvent.create(
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
            if event != expected_event:
                raise ValueError("checkpoint causal event identity is invalid")
            if (
                event.operation_artifact_id
                != checkpoint.operations[sequence].artifact_id
            ):
                raise ValueError("causal event operation dependency is invalid")
            if (
                event.transition_artifact_id
                != checkpoint.transitions[sequence].artifact_id
            ):
                raise ValueError("causal event transition dependency is invalid")
        if checkpoint.cancellation_signal is not None:
            signal = checkpoint.cancellation_signal
            expected_signal = (
                CancellationSignal.active(
                    reason=str(signal.reason),
                    request_artifact_id=str(signal.request_artifact_id),
                )
                if signal.requested
                else CancellationSignal.inactive()
            )
            if signal != expected_signal:
                raise ValueError("checkpoint cancellation identity is invalid")
        for sequence, failure in enumerate(checkpoint.failure_records):
            expected_failure = ResearchFailureRecord.create(
                sequence=sequence,
                role=failure.role,
                operation=failure.operation,
                kind=failure.kind,
                retryable=failure.retryable,
                exception_type=failure.exception_type,
                partial_evidence_artifact_ids=(failure.partial_evidence_artifact_ids),
            )
            if failure != expected_failure:
                raise ValueError("checkpoint failure identity is invalid")
        allowed_decisions = {
            item.artifact_id: item
            for item in checkpoint.tool_decisions
            if item.action is ToolPolicyAction.ALLOW
        }
        for sequence, record in enumerate(checkpoint.tool_execution_records):
            if record.sequence != sequence:
                raise ValueError("checkpoint tool executions are not contiguous")
            if record.descriptor_artifact_id not in (
                checkpoint.tool_descriptor_artifact_ids
            ):
                raise ValueError("checkpoint tool execution descriptor is unknown")
            decision = allowed_decisions.get(record.policy_decision_artifact_id)
            if decision is None:
                raise ValueError("checkpoint tool execution lacks an allow decision")
            if decision.invocation.request_sha256 != record.request_sha256:
                raise ValueError("checkpoint tool execution request identity differs")
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
                "tool_descriptor_artifact_ids": list(
                    checkpoint.tool_descriptor_artifact_ids
                ),
                "budget_policy_artifact_id": checkpoint.budget_policy_artifact_id,
                "retriever_descriptor_sha256": (checkpoint.retriever_descriptor_sha256),
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
                "tool_execution_record_artifact_ids": [
                    item.artifact_id for item in checkpoint.tool_execution_records
                ],
                "budget_decision_artifact_ids": [
                    item.artifact_id for item in checkpoint.budget_decisions
                ],
                "causal_event_artifact_ids": [
                    item.artifact_id for item in checkpoint.causal_events
                ],
                "cancellation_artifact_id": (
                    None
                    if checkpoint.cancellation_signal is None
                    else checkpoint.cancellation_signal.artifact_id
                ),
                "failure_artifact_ids": [
                    item.artifact_id for item in checkpoint.failure_records
                ],
                "cancellation_lineage": list(checkpoint.cancellation_lineage),
                "failure_lineage": list(checkpoint.failure_lineage),
            }
        ):
            raise ValueError("checkpoint content identity is invalid")
        current = self._checkpoint_payload(
            previous_checkpoint_artifact_id=(checkpoint.previous_checkpoint_artifact_id)
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
        if current["tool_descriptor_artifact_ids"] != list(
            checkpoint.tool_descriptor_artifact_ids
        ):
            raise ValueError("checkpoint dependency mismatch: tool descriptors")

    def _classify_failure(
        self, error: Exception, operation: ResearchOperation
    ) -> ResearchFailureRecord:
        if isinstance(error, ToolPolicyDenied):
            kind = ResearchFailureKind.POLICY_DENIED
            retryable = False
        elif isinstance(error, TimeoutError):
            kind = ResearchFailureKind.TIMEOUT
            retryable = True
        elif isinstance(error, ConnectionError) or bool(
            getattr(error, "transient", False)
        ):
            kind = ResearchFailureKind.RETRYABLE_TOOL
            retryable = True
        else:
            kind = ResearchFailureKind.PERMANENT_TOOL
            retryable = False
        partial: tuple[str, ...] = ()
        if self._retrieval is not None:
            partial = (self._retrieval.artifact_id,) + tuple(
                "sha256:" + str(record["source_text_sha256"])
                for record in self._retrieval.records
                if "source_text_sha256" in record
            )
        return ResearchFailureRecord.create(
            sequence=len(self._failure_records),
            role=self._role.value,
            operation=operation.value,
            kind=kind,
            retryable=retryable,
            exception_type=type(error).__name__,
            partial_evidence_artifact_ids=partial,
        )

    def _create_causal_event(
        self,
        *,
        record: ResearchOperationRecord,
        transition: ResearchTransition,
        tool_decision_start: int,
        budget_decision_start: int,
    ) -> CausalDecisionEvent:
        state_before = (
            "sha256:"
            + hashlib.sha256(
                _canonical(self._planning_input.model_dump(mode="json"))
            ).hexdigest()
            if not self._causal_events
            else self._transitions[-2].artifact_id
        )
        observations: tuple[str, ...] = ()
        evidence: tuple[str, ...] = ()
        outputs = [record.artifact_id]
        if self._retrieval is not None:
            observations = (self._retrieval.artifact_id,)
            evidence = tuple(
                "sha256:" + str(item["source_text_sha256"])
                for item in self._retrieval.records
                if "source_text_sha256" in item
            )
            if record.operation is ResearchOperation.RETRIEVE_EVIDENCE:
                outputs.append(self._retrieval.artifact_id)
        if self._reasoning is not None:
            evidence = tuple(
                dict.fromkeys(
                    evidence
                    + self._reasoning.evidence_artifact_ids
                    + self._reasoning.claim_artifact_ids
                )
            )
            if record.operation is ResearchOperation.SYNTHESIZE_ANSWER:
                outputs.append(self._reasoning.artifact_id)
        return CausalDecisionEvent.create(
            sequence=record.sequence,
            state_before_artifact_id=state_before,
            role=record.role.value,
            operation=record.operation.value,
            rationale=self._RATIONALE[record.operation],
            observation_artifact_ids=observations,
            evidence_artifact_ids=evidence,
            tool_decision_artifact_ids=tuple(
                item.artifact_id
                for item in self._services.decisions[tool_decision_start:]
            ),
            budget_decision_artifact_ids=tuple(
                item.artifact_id
                for item in self._budget.decisions[budget_decision_start:]
            ),
            policy_artifact_ids=(
                self._services.policy.artifact_id,
                self._budget.policy.artifact_id,
            ),
            output_artifact_ids=tuple(outputs),
            operation_artifact_id=record.artifact_id,
            transition_artifact_id=transition.artifact_id,
            state_after_artifact_id=transition.artifact_id,
        )


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
