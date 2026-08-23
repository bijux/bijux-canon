"""Fail-closed tool authority for bounded research execution."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json
from pathlib import Path

from bijux_canon_agent.contracts.execution_plan import ResearchPlanningInput


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


class ResearchTool(StrEnum):
    """Tools the Agent contract can explicitly authorize."""

    RETRIEVE = "bijux-canon-index.retrieve"
    INSPECT = "bijux-canon-runtime.inspect"
    REASON = "bijux-canon-reason.reason"
    FILESYSTEM_READ = "filesystem.read"


class ResearchToolOperation(StrEnum):
    """Single operations exposed by declared research tools."""

    RETRIEVE = "retrieve"
    INSPECT = "inspect"
    REASON = "reason"
    READ = "read"


class ToolPolicyAction(StrEnum):
    """The only possible policy outcomes."""

    ALLOW = "allow"
    DENY = "deny"


class ToolPolicyReason(StrEnum):
    """Stable reasons for auditable tool-policy decisions."""

    GRANTED = "granted"
    POLICY_PLAN_MISMATCH = "policy_plan_mismatch"
    TOOL_NOT_WHITELISTED = "tool_not_whitelisted"
    OPERATION_NOT_GRANTED = "operation_not_granted"
    CORPUS_SCOPE_DENIED = "corpus_scope_denied"
    INDEX_SCOPE_DENIED = "index_scope_denied"
    LOGICAL_SCOPE_DENIED = "logical_scope_denied"
    FILESYSTEM_SCOPE_DENIED = "filesystem_scope_denied"
    CALL_BUDGET_EXHAUSTED = "call_budget_exhausted"
    TIMEOUT_EXCEEDS_POLICY = "timeout_exceeds_policy"


_EXPECTED_OPERATION = {
    ResearchTool.RETRIEVE: ResearchToolOperation.RETRIEVE,
    ResearchTool.INSPECT: ResearchToolOperation.INSPECT,
    ResearchTool.REASON: ResearchToolOperation.REASON,
    ResearchTool.FILESYSTEM_READ: ResearchToolOperation.READ,
}


@dataclass(frozen=True, slots=True)
class ToolGrant:
    """Exact authority granted to one typed tool operation."""

    tool: ResearchTool
    operation: ResearchToolOperation
    corpus_generation: str
    index_generation: str
    scope: tuple[str, ...]
    filesystem_roots: tuple[str, ...]
    max_calls: int
    timeout_ms: int

    def __post_init__(self) -> None:
        if not isinstance(self.tool, ResearchTool):
            raise TypeError("tool grant tool must be ResearchTool")
        if not isinstance(self.operation, ResearchToolOperation):
            raise TypeError("tool grant operation must be ResearchToolOperation")
        if self.operation is not _EXPECTED_OPERATION[self.tool]:
            raise ValueError(f"operation {self.operation.value} does not match tool")
        if not self.corpus_generation.strip():
            raise ValueError("tool grant requires a corpus generation")
        if not self.index_generation.strip():
            raise ValueError("tool grant requires an index generation")
        if not self.scope or len(self.scope) != len(set(self.scope)):
            raise ValueError("tool grant scope must be nonempty and unique")
        if self.max_calls < 0:
            raise ValueError("tool grant max_calls must not be negative")
        if self.timeout_ms < 1:
            raise ValueError("tool grant timeout_ms must be positive")
        normalized_roots = tuple(
            _normalize_root(root) for root in self.filesystem_roots
        )
        if len(normalized_roots) != len(set(normalized_roots)):
            raise ValueError("tool grant filesystem roots must be unique")
        object.__setattr__(self, "filesystem_roots", normalized_roots)

    def payload(self) -> dict[str, object]:
        """Return the canonical grant payload used by policy identity."""
        return {
            "tool": self.tool.value,
            "operation": self.operation.value,
            "corpus_generation": self.corpus_generation,
            "index_generation": self.index_generation,
            "scope": list(self.scope),
            "filesystem_roots": list(self.filesystem_roots),
            "max_calls": self.max_calls,
            "timeout_ms": self.timeout_ms,
        }


@dataclass(frozen=True, slots=True)
class ToolInvocation:
    """Typed authority request made before a tool receives control."""

    tool: str
    operation: str
    plan_sha256: str
    request_sha256: str
    corpus_generation: str
    index_generation: str
    scope: tuple[str, ...]
    filesystem_paths: tuple[str, ...]
    timeout_ms: int
    tool_version: str = "1.0"
    input_schema_id: str = "policy-only.request.v1"
    output_schema_id: str = "policy-only.result.v1"
    capability: str = "policy-authorized-call"
    cost_units: int = 1
    idempotency_key: str | None = None
    replay_requested: bool = False

    def __post_init__(self) -> None:
        for name in (
            "tool",
            "operation",
            "corpus_generation",
            "index_generation",
        ):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"tool invocation {name} must not be empty")
        for name in ("plan_sha256", "request_sha256"):
            value = str(getattr(self, name))
            if len(value) != 64 or any(
                char not in "0123456789abcdef" for char in value
            ):
                raise ValueError(f"tool invocation {name} must be a SHA-256 digest")
        if not self.scope or len(self.scope) != len(set(self.scope)):
            raise ValueError("tool invocation scope must be nonempty and unique")
        if self.timeout_ms < 1:
            raise ValueError("tool invocation timeout_ms must be positive")
        for name in (
            "tool_version",
            "input_schema_id",
            "output_schema_id",
            "capability",
        ):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"tool invocation {name} must not be empty")
        if self.cost_units < 1:
            raise ValueError("tool invocation cost_units must be positive")
        if self.idempotency_key is not None:
            value = self.idempotency_key
            if len(value) != 64 or any(
                char not in "0123456789abcdef" for char in value
            ):
                raise ValueError("tool invocation idempotency_key must be SHA-256")
        normalized_paths = tuple(
            _normalize_path(path) for path in self.filesystem_paths
        )
        if len(normalized_paths) != len(set(normalized_paths)):
            raise ValueError("tool invocation filesystem paths must be unique")
        object.__setattr__(self, "filesystem_paths", normalized_paths)

    def payload(self) -> dict[str, object]:
        """Return every behavior-affecting invocation field."""
        return {
            "tool": self.tool,
            "operation": self.operation,
            "plan_sha256": self.plan_sha256,
            "request_sha256": self.request_sha256,
            "corpus_generation": self.corpus_generation,
            "index_generation": self.index_generation,
            "scope": list(self.scope),
            "filesystem_paths": list(self.filesystem_paths),
            "timeout_ms": self.timeout_ms,
            "tool_version": self.tool_version,
            "input_schema_id": self.input_schema_id,
            "output_schema_id": self.output_schema_id,
            "capability": self.capability,
            "cost_units": self.cost_units,
            "idempotency_key": self.idempotency_key,
            "replay_requested": self.replay_requested,
        }


@dataclass(frozen=True, slots=True)
class ToolPolicyDecision:
    """Content-addressed allow or deny decision for one invocation."""

    artifact_id: str
    sequence: int
    action: ToolPolicyAction
    reason: ToolPolicyReason
    policy_sha256: str
    invocation: ToolInvocation

    @classmethod
    def create(
        cls,
        *,
        sequence: int,
        action: ToolPolicyAction,
        reason: ToolPolicyReason,
        policy_sha256: str,
        invocation: ToolInvocation,
    ) -> ToolPolicyDecision:
        payload = {
            "sequence": sequence,
            "action": action.value,
            "reason": reason.value,
            "policy_sha256": policy_sha256,
            "invocation": invocation.payload(),
        }
        return cls(
            artifact_id="sha256:" + _sha256(payload),
            sequence=sequence,
            action=action,
            reason=reason,
            policy_sha256=policy_sha256,
            invocation=invocation,
        )


@dataclass(frozen=True, slots=True)
class ToolPolicy:
    """Immutable default-deny whitelist bound to one exact research plan."""

    plan_sha256: str
    grants: tuple[ToolGrant, ...]
    denied_tools: tuple[str, ...] = (
        "filesystem.write",
        "network.fetch",
        "subprocess.execute",
    )

    def __post_init__(self) -> None:
        if len(self.plan_sha256) != 64 or any(
            char not in "0123456789abcdef" for char in self.plan_sha256
        ):
            raise ValueError("tool policy plan_sha256 must be a SHA-256 digest")
        if any(not isinstance(grant, ToolGrant) for grant in self.grants):
            raise TypeError("tool policy grants must contain ToolGrant values")
        tools = [grant.tool for grant in self.grants]
        if len(tools) != len(set(tools)):
            raise ValueError("tool policy may grant each tool at most once")
        if tuple(sorted(tools, key=lambda tool: tool.value)) != tuple(tools):
            raise ValueError("tool policy grants must be sorted by tool")
        if len(self.denied_tools) != len(set(self.denied_tools)):
            raise ValueError("tool policy denied_tools must be unique")
        if tuple(sorted(self.denied_tools)) != self.denied_tools:
            raise ValueError("tool policy denied_tools must be sorted")
        granted_names = {tool.value for tool in tools}
        if granted_names.intersection(self.denied_tools):
            raise ValueError("a tool cannot be both granted and explicitly denied")

    @classmethod
    def for_plan(
        cls,
        planning_input: ResearchPlanningInput,
        *,
        filesystem_roots: Mapping[ResearchTool, tuple[str, ...]] | None = None,
    ) -> ToolPolicy:
        """Construct the minimal retrieval and reasoning authority for a plan."""
        roots = {} if filesystem_roots is None else filesystem_roots
        grants = (
            ToolGrant(
                tool=ResearchTool.RETRIEVE,
                operation=ResearchToolOperation.RETRIEVE,
                corpus_generation=planning_input.corpus_generation,
                index_generation=planning_input.index_generation,
                scope=planning_input.scope,
                filesystem_roots=roots.get(ResearchTool.RETRIEVE, ()),
                max_calls=planning_input.budget.retrievals,
                timeout_ms=planning_input.budget.elapsed_ms,
            ),
            ToolGrant(
                tool=ResearchTool.REASON,
                operation=ResearchToolOperation.REASON,
                corpus_generation=planning_input.corpus_generation,
                index_generation=planning_input.index_generation,
                scope=planning_input.scope,
                filesystem_roots=roots.get(ResearchTool.REASON, ()),
                max_calls=planning_input.budget.provider_calls,
                timeout_ms=planning_input.budget.elapsed_ms,
            ),
        )
        return cls(plan_sha256=plan_sha256(planning_input), grants=grants)

    @property
    def policy_sha256(self) -> str:
        """Return the stable identity of the complete policy."""
        return _sha256(
            {
                "default_action": "deny",
                "plan_sha256": self.plan_sha256,
                "grants": [grant.payload() for grant in self.grants],
                "denied_tools": list(self.denied_tools),
            }
        )

    @property
    def artifact_id(self) -> str:
        """Return the content-addressed policy artifact identifier."""
        return "sha256:" + self.policy_sha256

    def decide(
        self,
        invocation: ToolInvocation,
        *,
        sequence: int,
        prior_allowed_calls: int,
    ) -> ToolPolicyDecision:
        """Evaluate exact tool, scope, call, and timeout authority."""
        reason = self._denial_reason(invocation, prior_allowed_calls)
        action = ToolPolicyAction.ALLOW if reason is None else ToolPolicyAction.DENY
        return ToolPolicyDecision.create(
            sequence=sequence,
            action=action,
            reason=ToolPolicyReason.GRANTED if reason is None else reason,
            policy_sha256=self.policy_sha256,
            invocation=invocation,
        )

    def _denial_reason(
        self, invocation: ToolInvocation, prior_allowed_calls: int
    ) -> ToolPolicyReason | None:
        if invocation.plan_sha256 != self.plan_sha256:
            return ToolPolicyReason.POLICY_PLAN_MISMATCH
        grant = next(
            (item for item in self.grants if item.tool.value == invocation.tool), None
        )
        if grant is None or invocation.tool in self.denied_tools:
            return ToolPolicyReason.TOOL_NOT_WHITELISTED
        if invocation.operation != grant.operation.value:
            return ToolPolicyReason.OPERATION_NOT_GRANTED
        if invocation.corpus_generation != grant.corpus_generation:
            return ToolPolicyReason.CORPUS_SCOPE_DENIED
        if invocation.index_generation != grant.index_generation:
            return ToolPolicyReason.INDEX_SCOPE_DENIED
        if not set(invocation.scope).issubset(grant.scope):
            return ToolPolicyReason.LOGICAL_SCOPE_DENIED
        if not _paths_within_roots(invocation.filesystem_paths, grant.filesystem_roots):
            return ToolPolicyReason.FILESYSTEM_SCOPE_DENIED
        if prior_allowed_calls >= grant.max_calls:
            return ToolPolicyReason.CALL_BUDGET_EXHAUSTED
        if invocation.timeout_ms > grant.timeout_ms:
            return ToolPolicyReason.TIMEOUT_EXCEEDS_POLICY
        return None


def plan_sha256(planning_input: ResearchPlanningInput) -> str:
    """Hash every declared planning input for policy binding."""
    if not isinstance(planning_input, ResearchPlanningInput):
        raise TypeError("planning_input must be ResearchPlanningInput")
    return _sha256(planning_input.model_dump(mode="json"))


def _normalize_root(value: str) -> str:
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise ValueError("tool grant filesystem roots must be absolute")
    return str(path.resolve(strict=False))


def _normalize_path(value: str) -> str:
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise ValueError("tool invocation filesystem paths must be absolute")
    return str(path.resolve(strict=False))


def _paths_within_roots(paths: tuple[str, ...], roots: tuple[str, ...]) -> bool:
    resolved_roots = tuple(Path(root) for root in roots)
    return all(
        any(Path(path).is_relative_to(root) for root in resolved_roots)
        for path in paths
    )


__all__ = [
    "ResearchTool",
    "ResearchToolOperation",
    "ToolGrant",
    "ToolInvocation",
    "ToolPolicy",
    "ToolPolicyAction",
    "ToolPolicyDecision",
    "ToolPolicyReason",
    "plan_sha256",
]
