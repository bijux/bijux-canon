"""Durable evaluation of terminal research-agent behavior."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json

from bijux_canon_agent.application.research_workflow.state_machine import (
    ResearchExecutionResult,
    ResearchRole,
    ResearchRoleMachine,
)


class AgentBehaviorDimension(StrEnum):
    """Required dimensions of a trustworthy bounded-agent execution."""

    legal_transitions = "legal-transitions"
    tool_policy = "tool-policy"
    budget_compliance = "budget-compliance"
    causal_trace = "causal-trace"
    checkpoint = "checkpoint"
    failure_handling = "failure-handling"
    termination = "termination"


@dataclass(frozen=True, slots=True)
class AgentBehaviorOutcome:
    """One retained behavior check."""

    dimension: AgentBehaviorDimension
    passed: bool
    detail: str


@dataclass(frozen=True, slots=True)
class AgentBehaviorReport:
    """Content-addressed assessment of one terminal execution."""

    artifact_id: str
    execution_artifact_id: str
    outcomes: tuple[AgentBehaviorOutcome, ...]
    passed: bool

    def __post_init__(self) -> None:
        expected = tuple(AgentBehaviorDimension)
        if tuple(item.dimension for item in self.outcomes) != expected:
            raise ValueError("agent behavior dimensions are incomplete or unordered")
        if self.passed != all(item.passed for item in self.outcomes):
            raise ValueError("agent behavior report status is inconsistent")
        payload = {
            "execution_artifact_id": self.execution_artifact_id,
            "outcomes": [
                {
                    "dimension": item.dimension.value,
                    "passed": item.passed,
                    "detail": item.detail,
                }
                for item in self.outcomes
            ],
            "passed": self.passed,
        }
        if self.artifact_id != _artifact_id(payload):
            raise ValueError("agent behavior report identity does not match")


class AgentBehaviorEvaluator:
    """Audit policy, budget, causality, recovery, and termination together."""

    def evaluate(self, result: ResearchExecutionResult) -> AgentBehaviorReport:
        """Return every check without hiding a failed behavior dimension."""
        checks = (
            self._legal_transitions(result),
            self._tool_policy(result),
            self._budget(result),
            self._causal_trace(result),
            self._checkpoint(result),
            self._failure_handling(result),
            self._termination(result),
        )
        payload = {
            "execution_artifact_id": result.artifact_id,
            "outcomes": [
                {
                    "dimension": item.dimension.value,
                    "passed": item.passed,
                    "detail": item.detail,
                }
                for item in checks
            ],
            "passed": all(item.passed for item in checks),
        }
        return AgentBehaviorReport(
            artifact_id=_artifact_id(payload),
            execution_artifact_id=result.artifact_id,
            outcomes=checks,
            passed=all(item.passed for item in checks),
        )

    @staticmethod
    def _legal_transitions(result: ResearchExecutionResult) -> AgentBehaviorOutcome:
        passed = len(result.operations) == len(result.transitions)
        if passed:
            try:
                for operation, transition in zip(
                    result.operations, result.transitions, strict=True
                ):
                    ResearchRoleMachine.validate_transition(
                        from_role=transition.from_role,
                        to_role=transition.to_role,
                        operation=operation.operation,
                    )
                    if transition.operation_artifact_id != operation.artifact_id:
                        passed = False
            except ValueError:
                passed = False
        return _outcome(
            AgentBehaviorDimension.legal_transitions,
            passed,
            "every transition is legal and caused by its same-sequence operation",
        )

    @staticmethod
    def _tool_policy(result: ResearchExecutionResult) -> AgentBehaviorOutcome:
        passed = all(
            "sha256:" + item.policy_sha256 == result.tool_policy_artifact_id
            for item in result.tool_decisions
        )
        return _outcome(
            AgentBehaviorDimension.tool_policy,
            passed,
            "every tool decision is bound to the execution policy",
        )

    @staticmethod
    def _budget(result: ResearchExecutionResult) -> AgentBehaviorOutcome:
        passed = all(
            item.policy_artifact_id == result.budget_policy_artifact_id
            for item in result.budget_decisions
        )
        return _outcome(
            AgentBehaviorDimension.budget_compliance,
            passed,
            "every budget charge is bound to the execution budget policy",
        )

    @staticmethod
    def _causal_trace(result: ResearchExecutionResult) -> AgentBehaviorOutcome:
        passed = (
            len(result.causal_events) == len(result.operations)
            and result.causal_trace.event_artifact_ids
            == tuple(item.artifact_id for item in result.causal_events)
            and all(
                event.sequence == sequence
                and event.operation_artifact_id
                == result.operations[sequence].artifact_id
                and event.transition_artifact_id
                == result.transitions[sequence].artifact_id
                for sequence, event in enumerate(result.causal_events)
            )
        )
        return _outcome(
            AgentBehaviorDimension.causal_trace,
            passed,
            "causal events cover and bind every operation and transition",
        )

    @staticmethod
    def _checkpoint(result: ResearchExecutionResult) -> AgentBehaviorOutcome:
        passed = (
            bool(result.checkpoint_artifact_id)
            and bool(result.causal_events)
            and result.causal_events[-1].state_after_artifact_id
            == result.transitions[-1].artifact_id
        )
        return _outcome(
            AgentBehaviorDimension.checkpoint,
            passed,
            "terminal execution retains a checkpoint and final state lineage",
        )

    @staticmethod
    def _failure_handling(result: ResearchExecutionResult) -> AgentBehaviorOutcome:
        terminal = result.terminal_outcome
        passed = (
            (terminal.startswith("failed:") and bool(result.failure_records))
            or (
                terminal.startswith("cancelled:")
                and result.cancellation_signal is not None
            )
            or (
                terminal.startswith("budget_exhausted:")
                and bool(result.exhausted_budget_dimensions)
            )
            or (
                not terminal.startswith(("failed:", "cancelled:", "budget_exhausted:"))
                and not result.failure_records
            )
        )
        return _outcome(
            AgentBehaviorDimension.failure_handling,
            passed,
            "terminal outcome retains its failure, cancellation, or budget cause",
        )

    @staticmethod
    def _termination(result: ResearchExecutionResult) -> AgentBehaviorOutcome:
        passed = (
            bool(result.transitions)
            and result.transitions[-1].to_role is ResearchRole.TERMINAL
            and result.terminal_outcome != "incomplete"
        )
        return _outcome(
            AgentBehaviorDimension.termination,
            passed,
            "execution reaches the terminal role with an explicit outcome",
        )


def _outcome(
    dimension: AgentBehaviorDimension, passed: bool, detail: str
) -> AgentBehaviorOutcome:
    return AgentBehaviorOutcome(dimension=dimension, passed=passed, detail=detail)


def _artifact_id(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


__all__ = [
    "AgentBehaviorDimension",
    "AgentBehaviorEvaluator",
    "AgentBehaviorOutcome",
    "AgentBehaviorReport",
]
