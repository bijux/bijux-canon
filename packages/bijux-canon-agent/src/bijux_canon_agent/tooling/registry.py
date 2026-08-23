"""Fail-closed registry for typed, read-only research tools."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import time

from bijux_canon_agent.contracts.execution_control import (
    CancellationPort,
    CancellationSignal,
)
from bijux_canon_agent.contracts.tool_execution import (
    ResearchToolDescriptor,
    ToolExecutionRecord,
    ToolExecutionStatus,
    ToolReplayPolicy,
)
from bijux_canon_agent.contracts.tool_policy import (
    ToolInvocation,
    ToolPolicyAction,
    ToolPolicyDecision,
)

Identity = Callable[[object], str]
Summarizer = Callable[[object], Mapping[str, object]]
Executor = Callable[[object], object]


class ResearchToolRegistryError(RuntimeError):
    """Base class for registry refusals with no request or result payload."""


class UnknownResearchTool(ResearchToolRegistryError):
    """The requested name/version pair is not registered."""


class InvalidResearchToolCall(ResearchToolRegistryError):
    """A call does not match its registered schemas or authorization."""


class ResearchToolCallCancelled(ResearchToolRegistryError):
    """Cancellation prevented or invalidated a tool call."""


class ResearchToolReplayUnavailable(ResearchToolRegistryError):
    """Exact replay was requested without a matching recorded result."""


@dataclass(frozen=True, slots=True)
class ResearchToolBinding:
    """Trusted type and identity adapters for one public descriptor."""

    descriptor: ResearchToolDescriptor
    input_type: type[object]
    output_type: type[object]
    request_identity: Identity
    result_identity: Identity
    safe_summary: Summarizer

    def __post_init__(self) -> None:
        if not isinstance(self.descriptor, ResearchToolDescriptor):
            raise TypeError("tool binding descriptor must be ResearchToolDescriptor")
        if not isinstance(self.input_type, type) or not isinstance(
            self.output_type, type
        ):
            raise TypeError("tool binding schemas must be runtime types")
        if not all(
            callable(item)
            for item in (
                self.request_identity,
                self.result_identity,
                self.safe_summary,
            )
        ):
            raise TypeError("tool binding identity and summary adapters are required")


class ResearchToolRegistry:
    """Validate and execute only explicitly registered typed research tools."""

    def __init__(
        self,
        *,
        cancellation_port: CancellationPort | None = None,
        clock_ns: Callable[[], int] = time.monotonic_ns,
    ) -> None:
        if cancellation_port is not None and not isinstance(
            cancellation_port, CancellationPort
        ):
            raise TypeError("cancellation_port must implement CancellationPort")
        self._cancellation_port = cancellation_port
        self._clock_ns = clock_ns
        self._bindings: dict[tuple[str, str], ResearchToolBinding] = {}
        self._records: list[ToolExecutionRecord] = []
        self._replay: dict[
            tuple[str, str, str], tuple[str, object, ToolExecutionRecord]
        ] = {}

    @property
    def descriptors(self) -> tuple[ResearchToolDescriptor, ...]:
        """Return the registry inventory in stable name/version order."""
        return tuple(
            self._bindings[key].descriptor for key in sorted(self._bindings)
        )

    @property
    def records(self) -> tuple[ToolExecutionRecord, ...]:
        """Return every completed, refused, or failed execution attempt."""
        return tuple(self._records)

    def register(self, binding: ResearchToolBinding) -> None:
        """Register one immutable descriptor and its trusted type adapters."""
        if not isinstance(binding, ResearchToolBinding):
            raise TypeError("tool binding must be ResearchToolBinding")
        descriptor = binding.descriptor
        key = (descriptor.tool.value, descriptor.version)
        if key in self._bindings:
            raise ValueError("tool name and version are already registered")
        self._bindings[key] = binding

    def restore(
        self,
        records: tuple[ToolExecutionRecord, ...],
        decisions: tuple[ToolPolicyDecision, ...],
    ) -> None:
        """Restore validated call records without executing or rebuilding results."""
        if self._records or self._replay:
            raise RuntimeError("tool registry has already been used")
        descriptors = {
            binding.descriptor.artifact_id for binding in self._bindings.values()
        }
        decisions_by_id = {item.artifact_id: item for item in decisions}
        for sequence, record in enumerate(records):
            if not isinstance(record, ToolExecutionRecord):
                raise TypeError("restored tool calls must be ToolExecutionRecord")
            if record.sequence != sequence:
                raise ValueError("restored tool calls are not contiguous")
            if record.descriptor_artifact_id not in descriptors:
                raise ValueError("restored tool call has an unknown descriptor")
            decision = decisions_by_id.get(record.policy_decision_artifact_id)
            if decision is None or decision.action is not ToolPolicyAction.ALLOW:
                raise ValueError("restored tool call lacks its allow decision")
            if decision.invocation.request_sha256 != record.request_sha256:
                raise ValueError("restored tool call request identity differs")
            self._records.append(record)

    def execute(
        self,
        *,
        invocation: ToolInvocation,
        policy_decision: ToolPolicyDecision,
        request: object,
        executor: Executor,
    ) -> object:
        """Validate authority and schemas, then execute or replay one call."""
        if not isinstance(invocation, ToolInvocation):
            raise TypeError("invocation must be ToolInvocation")
        if not isinstance(policy_decision, ToolPolicyDecision):
            raise TypeError("policy_decision must be ToolPolicyDecision")
        if (
            policy_decision.action is not ToolPolicyAction.ALLOW
            or policy_decision.invocation != invocation
        ):
            raise InvalidResearchToolCall(
                "registry requires an allow decision for the exact invocation"
            )
        key = (invocation.tool, invocation.tool_version)
        binding = self._bindings.get(key)
        if binding is None:
            raise UnknownResearchTool("tool name/version is not registered")
        descriptor = binding.descriptor
        try:
            self._validate_descriptor_binding(invocation, descriptor)
        except InvalidResearchToolCall:
            self._record_failure(
                descriptor=descriptor,
                decision=policy_decision,
                invocation=invocation,
                status=ToolExecutionStatus.INVALID,
                failure_class="DescriptorBindingMismatch",
            )
            raise
        if not isinstance(request, binding.input_type):
            self._record_failure(
                descriptor=descriptor,
                decision=policy_decision,
                invocation=invocation,
                status=ToolExecutionStatus.INVALID,
                failure_class="InvalidInputSchema",
            )
            raise InvalidResearchToolCall("tool input does not match its schema")
        if binding.request_identity(request) != invocation.request_sha256:
            self._record_failure(
                descriptor=descriptor,
                decision=policy_decision,
                invocation=invocation,
                status=ToolExecutionStatus.INVALID,
                failure_class="RequestIdentityMismatch",
            )
            raise InvalidResearchToolCall("tool input identity does not match request")

        cancellation = self._cancellation()
        if cancellation.requested:
            self._record_failure(
                descriptor=descriptor,
                decision=policy_decision,
                invocation=invocation,
                status=ToolExecutionStatus.CANCELLED,
                failure_class="CancelledBeforeExecution",
                cancellation_artifact_id=cancellation.artifact_id,
            )
            raise ResearchToolCallCancelled("tool call cancelled before execution")

        replay_key = (
            invocation.tool,
            invocation.tool_version,
            invocation.idempotency_key or invocation.request_sha256,
        )
        recorded = self._replay.get(replay_key)
        if recorded is not None:
            recorded_request, result, source = recorded
            if recorded_request != invocation.request_sha256:
                self._record_failure(
                    descriptor=descriptor,
                    decision=policy_decision,
                    invocation=invocation,
                    status=ToolExecutionStatus.INVALID,
                    failure_class="IdempotencyIdentityConflict",
                )
                raise InvalidResearchToolCall(
                    "idempotency identity was reused for a different request"
                )
            if (
                descriptor.replay_policy is ToolReplayPolicy.RECORDED_ONLY
                and not invocation.replay_requested
            ):
                self._record_failure(
                    descriptor=descriptor,
                    decision=policy_decision,
                    invocation=invocation,
                    status=ToolExecutionStatus.INVALID,
                    failure_class="ExplicitReplayRequired",
                )
                raise ResearchToolReplayUnavailable(
                    "recorded-only tool result requires explicit replay"
                )
            record = self._record_success(
                descriptor=descriptor,
                decision=policy_decision,
                invocation=invocation,
                result=result,
                binding=binding,
                status=ToolExecutionStatus.REPLAYED,
                replay_source_artifact_id=source.artifact_id,
            )
            self._replay[replay_key] = (recorded_request, result, record)
            return result
        if invocation.replay_requested:
            self._record_failure(
                descriptor=descriptor,
                decision=policy_decision,
                invocation=invocation,
                status=ToolExecutionStatus.INVALID,
                failure_class="ReplayRecordUnavailable",
            )
            raise ResearchToolReplayUnavailable(
                "recorded replay is unavailable for this invocation"
            )

        started = self._clock_ns()
        try:
            result = executor(request)
        except Exception as error:
            self._record_failure(
                descriptor=descriptor,
                decision=policy_decision,
                invocation=invocation,
                status=ToolExecutionStatus.FAILED,
                failure_class=type(error).__name__,
            )
            raise
        elapsed_ms = max(0, (self._clock_ns() - started) // 1_000_000)
        if elapsed_ms > invocation.timeout_ms:
            self._record_failure(
                descriptor=descriptor,
                decision=policy_decision,
                invocation=invocation,
                status=ToolExecutionStatus.TIMED_OUT,
                failure_class="ToolTimeout",
            )
            raise TimeoutError("registered tool exceeded its declared timeout")
        cancellation = self._cancellation()
        if cancellation.requested:
            self._record_failure(
                descriptor=descriptor,
                decision=policy_decision,
                invocation=invocation,
                status=ToolExecutionStatus.CANCELLED,
                failure_class="CancelledDuringExecution",
                cancellation_artifact_id=cancellation.artifact_id,
            )
            raise ResearchToolCallCancelled("tool call cancelled during execution")
        if not isinstance(result, binding.output_type):
            self._record_failure(
                descriptor=descriptor,
                decision=policy_decision,
                invocation=invocation,
                status=ToolExecutionStatus.INVALID,
                failure_class="InvalidOutputSchema",
            )
            raise InvalidResearchToolCall("tool output does not match its schema")
        try:
            record = self._record_success(
                descriptor=descriptor,
                decision=policy_decision,
                invocation=invocation,
                result=result,
                binding=binding,
                status=ToolExecutionStatus.SUCCEEDED,
            )
        except (TypeError, ValueError) as error:
            self._record_failure(
                descriptor=descriptor,
                decision=policy_decision,
                invocation=invocation,
                status=ToolExecutionStatus.INVALID,
                failure_class="InvalidResultIdentityOrSummary",
            )
            raise InvalidResearchToolCall(
                "tool result identity or safe summary is invalid"
            ) from error
        if descriptor.replay_policy in {
            ToolReplayPolicy.RECORDED_ONLY,
            ToolReplayPolicy.IDEMPOTENT_READ,
        }:
            self._replay[replay_key] = (invocation.request_sha256, result, record)
        return result

    def _validate_descriptor_binding(
        self,
        invocation: ToolInvocation,
        descriptor: ResearchToolDescriptor,
    ) -> None:
        actual = (
            invocation.operation,
            invocation.input_schema_id,
            invocation.output_schema_id,
            invocation.capability,
            invocation.cost_units,
        )
        expected = (
            descriptor.operation.value,
            descriptor.input_schema_id,
            descriptor.output_schema_id,
            descriptor.capability,
            descriptor.cost_units,
        )
        if actual != expected:
            raise InvalidResearchToolCall(
                "tool invocation does not match the registered descriptor"
            )

    def _cancellation(self) -> CancellationSignal:
        if self._cancellation_port is None:
            return CancellationSignal.inactive()
        signal = self._cancellation_port.current()
        if not isinstance(signal, CancellationSignal):
            raise TypeError("cancellation port returned an invalid signal")
        return signal

    def _record_success(
        self,
        *,
        descriptor: ResearchToolDescriptor,
        decision: ToolPolicyDecision,
        invocation: ToolInvocation,
        result: object,
        binding: ResearchToolBinding,
        status: ToolExecutionStatus,
        replay_source_artifact_id: str | None = None,
    ) -> ToolExecutionRecord:
        result_artifact_id = binding.result_identity(result)
        record = ToolExecutionRecord.create(
            sequence=len(self._records),
            descriptor=descriptor,
            policy_decision=decision,
            invocation=invocation,
            result_artifact_id=result_artifact_id,
            status=status,
            safe_summary=binding.safe_summary(result),
            replay_source_artifact_id=replay_source_artifact_id,
        )
        self._records.append(record)
        return record

    def _record_failure(
        self,
        *,
        descriptor: ResearchToolDescriptor,
        decision: ToolPolicyDecision,
        invocation: ToolInvocation,
        status: ToolExecutionStatus,
        failure_class: str,
        cancellation_artifact_id: str | None = None,
    ) -> None:
        summary = (
            {"status": status.value}
            if "status" in descriptor.safe_summary_fields
            else {}
        )
        self._records.append(
            ToolExecutionRecord.create(
                sequence=len(self._records),
                descriptor=descriptor,
                policy_decision=decision,
                invocation=invocation,
                result_artifact_id=None,
                status=status,
                safe_summary=summary,
                cancellation_artifact_id=cancellation_artifact_id,
                failure_class=failure_class,
            )
        )


__all__ = [
    "InvalidResearchToolCall",
    "ResearchToolBinding",
    "ResearchToolCallCancelled",
    "ResearchToolRegistry",
    "ResearchToolRegistryError",
    "ResearchToolReplayUnavailable",
    "UnknownResearchTool",
]
