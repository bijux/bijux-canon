"""Deterministic global and per-role research budget accounting."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from enum import StrEnum
import hashlib
import json
from types import MappingProxyType
from typing import Mapping

from bijux_canon_agent.contracts.execution_plan import (
    PlanningBudget,
    ResearchPlanningInput,
)
from bijux_canon_agent.contracts.tool_policy import plan_sha256


def _artifact_id(value: object) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class BudgetDimensions:
    """Usage or limits across every declared research resource dimension."""

    iterations: int = 0
    retrievals: int = 0
    candidates: int = 0
    evidence_items: int = 0
    tool_calls: int = 0
    provider_calls: int = 0
    tokens: int = 0
    elapsed_ms: int = 0
    retries: int = 0
    artifact_bytes: int = 0

    def __post_init__(self) -> None:
        if any(getattr(self, item.name) < 0 for item in fields(self)):
            raise ValueError("budget dimensions must not be negative")

    @classmethod
    def from_plan(cls, budget: PlanningBudget) -> BudgetDimensions:
        """Project every planning ceiling without dropping dimensions."""
        return cls(**budget.model_dump(mode="python"))

    def plus(self, other: BudgetDimensions) -> BudgetDimensions:
        """Add a deterministic charge to current usage."""
        return BudgetDimensions(
            **{
                item.name: getattr(self, item.name) + getattr(other, item.name)
                for item in fields(self)
            }
        )

    def exceeded(self, limits: BudgetDimensions) -> tuple[str, ...]:
        """Return exceeded dimensions in declaration order."""
        return tuple(
            item.name
            for item in fields(self)
            if getattr(self, item.name) > getattr(limits, item.name)
        )

    def payload(self) -> dict[str, int]:
        return asdict(self)


class BudgetAction(StrEnum):
    """Whether a deterministic charge may proceed."""

    CONTINUE = "continue"
    TERMINATE = "terminate"


@dataclass(frozen=True, slots=True)
class ResearchBudgetPolicy:
    """Immutable global and per-role ceilings bound to one plan."""

    plan_sha256: str
    global_limits: BudgetDimensions
    role_limits: Mapping[str, BudgetDimensions]

    def __post_init__(self) -> None:
        if len(self.plan_sha256) != 64 or any(
            char not in "0123456789abcdef" for char in self.plan_sha256
        ):
            raise ValueError("budget policy requires a plan SHA-256")
        if not self.role_limits:
            raise ValueError("budget policy requires per-role limits")
        if any(not role.strip() for role in self.role_limits):
            raise ValueError("budget policy role names must not be empty")
        object.__setattr__(
            self,
            "role_limits",
            MappingProxyType(dict(sorted(self.role_limits.items()))),
        )

    @classmethod
    def for_plan(
        cls, planning_input: ResearchPlanningInput
    ) -> ResearchBudgetPolicy:
        """Create explicit ceilings for every role in the fixed role machine."""
        limits = BudgetDimensions.from_plan(planning_input.budget)
        role_limits = {
            role: BudgetDimensions(
                iterations=1,
                retrievals=limits.retrievals if role == "retrieve" else 0,
                candidates=limits.candidates if role == "retrieve" else 0,
                evidence_items=(
                    limits.evidence_items if role == "retrieve" else 0
                ),
                tool_calls=limits.tool_calls if role == "retrieve" else 0,
                provider_calls=(
                    limits.provider_calls if role == "synthesize" else 0
                ),
                tokens=limits.tokens if role == "synthesize" else 0,
                elapsed_ms=limits.elapsed_ms,
                retries=limits.retries,
                artifact_bytes=limits.artifact_bytes,
            )
            for role in (
                "plan",
                "retrieve",
                "analyze",
                "skeptic",
                "gap_fill",
                "synthesize",
                "verify",
                "terminate",
            )
        }
        return cls(
            plan_sha256=plan_sha256(planning_input),
            global_limits=limits,
            role_limits=role_limits,
        )

    @property
    def artifact_id(self) -> str:
        """Return the stable identity of global and per-role limits."""
        return _artifact_id(
            {
                "plan_sha256": self.plan_sha256,
                "global_limits": self.global_limits.payload(),
                "role_limits": {
                    role: limits.payload()
                    for role, limits in self.role_limits.items()
                },
            }
        )


@dataclass(frozen=True, slots=True)
class BudgetDecision:
    """Content-addressed result of applying one usage charge."""

    artifact_id: str
    sequence: int
    policy_artifact_id: str
    role: str
    label: str
    action: BudgetAction
    charge: BudgetDimensions
    global_usage: BudgetDimensions
    role_usage: BudgetDimensions
    exhausted_dimensions: tuple[str, ...]

    @classmethod
    def create(
        cls,
        *,
        sequence: int,
        policy_artifact_id: str,
        role: str,
        label: str,
        action: BudgetAction,
        charge: BudgetDimensions,
        global_usage: BudgetDimensions,
        role_usage: BudgetDimensions,
        exhausted_dimensions: tuple[str, ...],
    ) -> BudgetDecision:
        payload = {
            "sequence": sequence,
            "policy_artifact_id": policy_artifact_id,
            "role": role,
            "label": label,
            "action": action.value,
            "charge": charge.payload(),
            "global_usage": global_usage.payload(),
            "role_usage": role_usage.payload(),
            "exhausted_dimensions": list(exhausted_dimensions),
        }
        return cls(
            artifact_id=_artifact_id(payload),
            sequence=sequence,
            policy_artifact_id=policy_artifact_id,
            role=role,
            label=label,
            action=action,
            charge=charge,
            global_usage=global_usage,
            role_usage=role_usage,
            exhausted_dimensions=exhausted_dimensions,
        )


class ResearchBudgetLedger:
    """Apply atomic charges against global and per-role ceilings."""

    def __init__(self, policy: ResearchBudgetPolicy) -> None:
        if not isinstance(policy, ResearchBudgetPolicy):
            raise TypeError("policy must be ResearchBudgetPolicy")
        self._policy = policy
        self._global_usage = BudgetDimensions()
        self._role_usage = {
            role: BudgetDimensions() for role in policy.role_limits
        }
        self._decisions: list[BudgetDecision] = []
        self._exhausted: tuple[str, ...] = ()

    @property
    def policy(self) -> ResearchBudgetPolicy:
        return self._policy

    @property
    def global_usage(self) -> BudgetDimensions:
        return self._global_usage

    @property
    def decisions(self) -> tuple[BudgetDecision, ...]:
        return tuple(self._decisions)

    @property
    def exhausted_dimensions(self) -> tuple[str, ...]:
        return self._exhausted

    def charge(
        self, *, role: str, label: str, usage: BudgetDimensions
    ) -> BudgetDecision:
        """Record a charge and deterministically stop on either ceiling."""
        if role not in self._policy.role_limits:
            raise ValueError(f"budget policy has no limits for role {role}")
        if self._exhausted:
            decision = BudgetDecision.create(
                sequence=len(self._decisions),
                policy_artifact_id=self._policy.artifact_id,
                role=role,
                label=label,
                action=BudgetAction.TERMINATE,
                charge=BudgetDimensions(),
                global_usage=self._global_usage,
                role_usage=self._role_usage[role],
                exhausted_dimensions=self._exhausted,
            )
            self._decisions.append(decision)
            return decision
        global_usage = self._global_usage.plus(usage)
        role_usage = self._role_usage[role].plus(usage)
        global_exceeded = global_usage.exceeded(self._policy.global_limits)
        role_exceeded = tuple(
            f"{role}.{name}"
            for name in role_usage.exceeded(self._policy.role_limits[role])
        )
        exhausted = global_exceeded + role_exceeded
        action = BudgetAction.TERMINATE if exhausted else BudgetAction.CONTINUE
        self._global_usage = global_usage
        self._role_usage[role] = role_usage
        self._exhausted = exhausted
        decision = BudgetDecision.create(
            sequence=len(self._decisions),
            policy_artifact_id=self._policy.artifact_id,
            role=role,
            label=label,
            action=action,
            charge=usage,
            global_usage=global_usage,
            role_usage=role_usage,
            exhausted_dimensions=exhausted,
        )
        self._decisions.append(decision)
        return decision


__all__ = [
    "BudgetAction",
    "BudgetDecision",
    "BudgetDimensions",
    "ResearchBudgetLedger",
    "ResearchBudgetPolicy",
]
