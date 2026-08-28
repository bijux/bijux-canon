"""Contract and enforcement tests for the typed research-tool registry."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import cast

import pytest

from bijux_canon_agent.contracts import (
    CancellationSignal,
    ResearchTool,
    ResearchToolDescriptor,
    ResearchToolOperation,
    ToolExecutionStatus,
    ToolGrant,
    ToolInvocation,
    ToolPolicy,
    ToolPolicyDecision,
    ToolReplayPolicy,
)
from bijux_canon_agent.tooling import (
    InvalidResearchToolCall,
    ResearchToolBinding,
    ResearchToolCallCancelled,
    ResearchToolRegistry,
    ResearchToolReplayUnavailable,
    UnknownResearchTool,
)

_PLAN = "1" * 64
_REQUEST = "2" * 64
_RESULT = "sha256:" + "3" * 64
_IDEMPOTENCY = "4" * 64


@dataclass(frozen=True)
class _Request:
    identity: str = _REQUEST


@dataclass(frozen=True)
class _Result:
    artifact_id: str = _RESULT
    count: int = 3
    secret: str = "must-not-be-recorded"


class _Cancellation:
    def __init__(self, *signals: CancellationSignal) -> None:
        self._signals = list(signals) or [CancellationSignal.inactive()]

    def current(self) -> CancellationSignal:
        if len(self._signals) > 1:
            return self._signals.pop(0)
        return self._signals[0]


def _descriptor() -> ResearchToolDescriptor:
    return ResearchToolDescriptor(
        tool=ResearchTool.RETRIEVE,
        operation=ResearchToolOperation.RETRIEVE,
        version="1.0",
        input_schema_id="bijux.canon.index.query.v1",
        output_schema_id="bijux.canon.index.result.v1",
        capability="corpus-retrieval",
        owner_distribution="bijux-canon-index",
        implementation="bijux_canon_index.application.IndexService.query",
        replay_policy=ToolReplayPolicy.IDEMPOTENT_READ,
        cost_units=1,
        safe_summary_fields=("artifact_id", "record_count", "status"),
    )


def _policy(*, max_calls: int = 4) -> ToolPolicy:
    return ToolPolicy(
        plan_sha256=_PLAN,
        grants=(
            ToolGrant(
                tool=ResearchTool.RETRIEVE,
                operation=ResearchToolOperation.RETRIEVE,
                corpus_generation="corpus-1",
                index_generation="index-1",
                scope=("source:one",),
                filesystem_roots=(),
                max_calls=max_calls,
                timeout_ms=100,
            ),
        ),
    )


def _invocation(**changes: object) -> ToolInvocation:
    values: dict[str, object] = {
        "tool": ResearchTool.RETRIEVE.value,
        "operation": ResearchToolOperation.RETRIEVE.value,
        "plan_sha256": _PLAN,
        "request_sha256": _REQUEST,
        "corpus_generation": "corpus-1",
        "index_generation": "index-1",
        "scope": ("source:one",),
        "filesystem_paths": (),
        "timeout_ms": 100,
        "tool_version": "1.0",
        "input_schema_id": "bijux.canon.index.query.v1",
        "output_schema_id": "bijux.canon.index.result.v1",
        "capability": "corpus-retrieval",
        "cost_units": 1,
        "idempotency_key": _IDEMPOTENCY,
    }
    values.update(changes)
    return ToolInvocation(**values)  # type: ignore[arg-type]


def _registry(
    *,
    cancellation: _Cancellation | None = None,
    clock_ns: Callable[[], int] = lambda: 0,
    descriptor: ResearchToolDescriptor | None = None,
) -> ResearchToolRegistry:
    registry = ResearchToolRegistry(
        cancellation_port=cancellation,
        clock_ns=clock_ns,
    )
    registry.register(
        ResearchToolBinding(
            descriptor=descriptor or _descriptor(),
            input_type=_Request,
            output_type=_Result,
            request_identity=lambda request: cast(_Request, request).identity,
            result_identity=lambda result: cast(_Result, result).artifact_id,
            safe_summary=lambda result: {
                "artifact_id": cast(_Result, result).artifact_id,
                "record_count": cast(_Result, result).count,
                "status": "available",
            },
        )
    )
    return registry


def _allow(
    invocation: ToolInvocation,
    *,
    sequence: int = 0,
    prior: int = 0,
) -> ToolPolicyDecision:
    return _policy().decide(
        invocation,
        sequence=sequence,
        prior_allowed_calls=prior,
    )


def test_registry_binds_descriptor_schema_and_safe_result_lineage() -> None:
    registry = _registry()
    invocation = _invocation()
    calls: list[_Request] = []

    def execute(request: object) -> object:
        assert isinstance(request, _Request)
        calls.append(request)
        return _Result()

    result = registry.execute(
        invocation=invocation,
        policy_decision=_allow(invocation),
        request=_Request(),
        executor=execute,
    )

    assert result == _Result()
    assert calls == [_Request()]
    assert registry.descriptors == (_descriptor(),)
    record = registry.records[0]
    assert record.status is ToolExecutionStatus.SUCCEEDED
    assert record.request_sha256 == _REQUEST
    assert record.result_artifact_id == _RESULT
    assert record.safe_summary == {
        "artifact_id": _RESULT,
        "record_count": 3,
        "status": "available",
    }
    assert "must-not-be-recorded" not in repr(record)


def test_registry_rejects_unknown_version_and_invalid_schema_before_execution() -> None:
    registry = _registry()
    calls: list[object] = []
    unknown = _invocation(tool_version="2.0")
    with pytest.raises(UnknownResearchTool):
        registry.execute(
            invocation=unknown,
            policy_decision=_allow(unknown),
            request=_Request(),
            executor=lambda request: calls.append(request),
        )
    invalid = _invocation(input_schema_id="attacker.schema.v1")
    with pytest.raises(InvalidResearchToolCall, match="descriptor"):
        registry.execute(
            invocation=invalid,
            policy_decision=_allow(invalid),
            request=_Request(),
            executor=lambda request: calls.append(request),
        )
    invalid_cost = _invocation(cost_units=99)
    with pytest.raises(InvalidResearchToolCall, match="descriptor"):
        registry.execute(
            invocation=invalid_cost,
            policy_decision=_allow(invalid_cost),
            request=_Request(),
            executor=lambda request: calls.append(request),
        )
    assert calls == []


def test_registry_requires_exact_allow_decision_before_execution() -> None:
    registry = _registry()
    invocation = _invocation(scope=("source:outside",))
    denied = _policy().decide(
        invocation,
        sequence=0,
        prior_allowed_calls=0,
    )
    calls: list[object] = []

    with pytest.raises(InvalidResearchToolCall, match="allow decision"):
        registry.execute(
            invocation=invocation,
            policy_decision=denied,
            request=_Request(),
            executor=lambda request: calls.append(request),
        )
    assert calls == []


def test_registry_enforces_cancellation_before_and_during_call() -> None:
    cancelled = CancellationSignal.active(
        reason="operator stop",
        request_artifact_id="sha256:" + "5" * 64,
    )
    before = _registry(cancellation=_Cancellation(cancelled))
    invocation = _invocation()
    with pytest.raises(ResearchToolCallCancelled, match="before"):
        before.execute(
            invocation=invocation,
            policy_decision=_allow(invocation),
            request=_Request(),
            executor=lambda request: _Result(),
        )
    assert before.records[0].cancellation_artifact_id == cancelled.artifact_id

    during = _registry(
        cancellation=_Cancellation(CancellationSignal.inactive(), cancelled)
    )
    with pytest.raises(ResearchToolCallCancelled, match="during"):
        during.execute(
            invocation=invocation,
            policy_decision=_allow(invocation),
            request=_Request(),
            executor=lambda request: _Result(),
        )
    assert during.records[0].result_artifact_id is None


def test_registry_enforces_timeout_without_recording_result_payload() -> None:
    times = iter((0, 2_000_000))
    registry = _registry(clock_ns=lambda: next(times))
    invocation = _invocation(timeout_ms=1)

    with pytest.raises(TimeoutError, match="declared timeout"):
        registry.execute(
            invocation=invocation,
            policy_decision=_allow(invocation),
            request=_Request(),
            executor=lambda request: _Result(),
        )

    assert registry.records[0].status is ToolExecutionStatus.TIMED_OUT
    assert registry.records[0].result_artifact_id is None


def test_registry_replays_idempotently_and_refuses_missing_recorded_replay() -> None:
    registry = _registry()
    first = _invocation()
    replay = _invocation(replay_requested=True)
    calls: list[str] = []

    def first_execution(request: object) -> object:
        calls.append("first")
        return _Result()

    def unexpected_replay(request: object) -> object:
        calls.append("replay")
        return _Result()

    registry.execute(
        invocation=first,
        policy_decision=_allow(first),
        request=_Request(),
        executor=first_execution,
    )
    result = registry.execute(
        invocation=replay,
        policy_decision=_allow(replay, sequence=1, prior=1),
        request=_Request(),
        executor=unexpected_replay,
    )

    assert result == _Result()
    assert calls == ["first"]
    assert registry.records[-1].status is ToolExecutionStatus.REPLAYED
    assert registry.records[-1].replay_source_artifact_id == (
        registry.records[0].artifact_id
    )

    conflicting_request = "6" * 64
    conflict = _invocation(request_sha256=conflicting_request)
    with pytest.raises(InvalidResearchToolCall, match="different request"):
        registry.execute(
            invocation=conflict,
            policy_decision=_allow(conflict, sequence=2, prior=2),
            request=_Request(identity=conflicting_request),
            executor=unexpected_replay,
        )
    assert calls == ["first"]
    assert registry.records[-1].failure_class == "IdempotencyIdentityConflict"

    missing = _registry()
    with pytest.raises(ResearchToolReplayUnavailable):
        missing.execute(
            invocation=replay,
            policy_decision=_allow(replay),
            request=_Request(),
            executor=lambda request: pytest.fail("replay must not execute"),
        )


def test_recorded_only_result_requires_an_explicit_replay_request() -> None:
    descriptor = replace(
        _descriptor(),
        replay_policy=ToolReplayPolicy.RECORDED_ONLY,
    )
    registry = _registry(descriptor=descriptor)
    invocation = _invocation()
    registry.execute(
        invocation=invocation,
        policy_decision=_allow(invocation),
        request=_Request(),
        executor=lambda request: _Result(),
    )

    with pytest.raises(ResearchToolReplayUnavailable, match="explicit replay"):
        registry.execute(
            invocation=invocation,
            policy_decision=_allow(invocation, sequence=1, prior=1),
            request=_Request(),
            executor=lambda request: pytest.fail("duplicate must not execute"),
        )


def test_descriptor_and_record_refuse_secret_summary_fields() -> None:
    with pytest.raises(ValueError, match="secret material"):
        replace(
            _descriptor(),
            safe_summary_fields=("api_key", "status"),
        )
