# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Dispatch each typed Runtime DAG node to exactly one operation adapter."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from time import monotonic
from types import MappingProxyType
from typing import Protocol

from bijux_canon_runtime.model.artifact import AddressedArtifact, describe_artifact
from bijux_canon_runtime.model.execution.request_plan import (
    ConcreteDagStep,
    DagOperation,
    RuntimeRequestPlan,
)
from bijux_canon_runtime.ontology.ids import ArtifactID, ContentHash


class StepDispatchError(RuntimeError):
    """A typed step could not be dispatched without violating its contract."""


class StepDispatchCancelled(StepDispatchError):
    """Execution was cancelled before a step artifact could be accepted."""


class StepDispatchTimedOut(StepDispatchError):
    """Execution exceeded its deadline before outputs could be accepted."""


def _never_cancelled() -> bool:
    return False


@dataclass(frozen=True, slots=True)
class StepDispatchContext:
    """Cooperative cancellation and deadline boundary for one adapter call."""

    is_cancelled: Callable[[], bool] = _never_cancelled
    deadline_monotonic: float | None = None
    monotonic_clock: Callable[[], float] = monotonic
    run_id: str | None = None
    execution_manifest_artifact_id: ArtifactID | None = None

    @property
    def remaining_seconds(self) -> float | None:
        """Return the bounded provider timeout available at this instant."""
        if self.deadline_monotonic is None:
            return None
        return max(0.0, self.deadline_monotonic - self.monotonic_clock())

    def raise_if_stopped(self) -> None:
        """Distinguish caller cancellation from deadline exhaustion."""
        if self.is_cancelled():
            raise StepDispatchCancelled("step dispatch was cancelled")
        if (
            self.deadline_monotonic is not None
            and self.monotonic_clock() >= self.deadline_monotonic
        ):
            raise StepDispatchTimedOut("step dispatch deadline was exceeded")

    def raise_if_cancelled(self) -> None:
        """Retain the established cooperative checkpoint API."""
        self.raise_if_stopped()


@dataclass(frozen=True, slots=True)
class StepOutputArtifact:
    """Validated content-addressed output from exactly one DAG step."""

    contract_id: str
    producer_step_id: str
    producer_operation: DagOperation
    artifact: AddressedArtifact

    @property
    def artifact_id(self) -> ArtifactID:
        """Return the schema-bound immutable artifact identity."""
        return self.artifact.descriptor.artifact_id

    @property
    def media_type(self) -> str:
        """Return the concrete media type validated by the artifact model."""
        return self.artifact.descriptor.media_type

    @property
    def content_sha256(self) -> ContentHash:
        """Return the canonical payload digest."""
        return self.artifact.descriptor.payload_sha256

    @property
    def payload(self) -> bytes:
        """Return the immutable canonical payload bytes."""
        return self.artifact.canonical_bytes

    @classmethod
    def from_payload(
        cls,
        *,
        step: ConcreteDagStep,
        contract_id: str,
        media_type: str,
        payload: bytes,
        dependencies: tuple[StepOutputArtifact, ...] = (),
        dependency_artifact_ids: tuple[ArtifactID, ...] = (),
    ) -> StepOutputArtifact:
        """Create an artifact whose identity is bound to its payload bytes."""
        dependency_ids = tuple(
            sorted(
                {
                    *(item.artifact_id for item in dependencies),
                    *dependency_artifact_ids,
                }
            )
        )
        addressed = AddressedArtifact.from_bytes(
            payload,
            schema_id=contract_id,
            media_type=media_type,
            producer=f"bijux-canon-runtime:{step.operation.value}",
            dependencies=dependency_ids,
        )
        return cls(
            contract_id=contract_id,
            producer_step_id=step.step_id,
            producer_operation=step.operation,
            artifact=addressed,
        )

    def validate(self) -> None:
        """Validate identity, ownership, media type, and payload integrity."""
        if not self.contract_id.strip() or not self.producer_step_id.strip():
            raise StepDispatchError("step artifact ownership must not be empty")
        descriptor = self.artifact.descriptor
        if descriptor.schema_id != self.contract_id:
            raise StepDispatchError("step artifact schema does not match its contract")
        if descriptor.producer != (
            f"bijux-canon-runtime:{self.producer_operation.value}"
        ):
            raise StepDispatchError("step artifact producer metadata does not match")
        expected = describe_artifact(
            canonical_bytes=self.artifact.canonical_bytes,
            schema_id=descriptor.schema_id,
            media_type=descriptor.media_type,
            producer=descriptor.producer,
            dependencies=descriptor.dependencies,
        )
        if descriptor != expected:
            raise StepDispatchError(
                "step artifact descriptor does not match its payload"
            )


class OperationAdapter(Protocol):
    """Versioned port for one and only one typed DAG operation."""

    @property
    def adapter_id(self) -> str:
        """Return a stable adapter identity."""
        ...

    @property
    def adapter_version(self) -> str:
        """Return the adapter contract implementation version."""
        ...

    @property
    def operation(self) -> DagOperation:
        """Return the exclusive operation implemented by this adapter."""
        ...

    def execute(
        self,
        step: ConcreteDagStep,
        upstream_artifacts: tuple[StepOutputArtifact, ...],
        context: StepDispatchContext,
    ) -> tuple[StepOutputArtifact, ...]:
        """Execute exactly the behavior named by ``operation``."""
        ...


@dataclass(frozen=True, slots=True)
class StepDispatchResult:
    """Auditable result of one exclusive adapter invocation."""

    step_id: str
    operation: DagOperation
    adapter_id: str
    adapter_version: str
    artifacts: tuple[StepOutputArtifact, ...]


class OperationDispatcher:
    """Resolve typed nodes to explicit adapters without generic fallbacks."""

    def __init__(self, adapters: Iterable[OperationAdapter]) -> None:
        by_operation: dict[DagOperation, OperationAdapter] = {}
        for adapter in adapters:
            if not adapter.adapter_id.strip() or not adapter.adapter_version.strip():
                raise ValueError("operation adapter identity and version are required")
            if adapter.operation in by_operation:
                raise ValueError(
                    f"duplicate adapter for operation {adapter.operation.value}"
                )
            by_operation[adapter.operation] = adapter
        self._adapters = MappingProxyType(by_operation)

    def dispatch(
        self,
        step: ConcreteDagStep,
        upstream_artifacts: tuple[StepOutputArtifact, ...] = (),
        *,
        context: StepDispatchContext | None = None,
    ) -> StepDispatchResult:
        """Invoke one operation adapter and validate its complete artifact set."""
        dispatch_context = context or StepDispatchContext()
        dispatch_context.raise_if_stopped()
        self._validate_upstream(step, upstream_artifacts)
        adapter = self._adapters.get(step.operation)
        if adapter is None:
            raise StepDispatchError(
                f"no adapter registered for operation {step.operation.value}"
            )
        try:
            artifacts = adapter.execute(step, upstream_artifacts, dispatch_context)
        except StepDispatchError:
            raise
        except Exception as exc:
            raise StepDispatchError(
                f"adapter {adapter.adapter_id} failed operation {step.operation.value}"
            ) from exc
        try:
            dispatch_context.raise_if_stopped()
        except StepDispatchCancelled:
            cancellation_validator = getattr(
                adapter,
                "accepts_cooperative_cancellation",
                None,
            )
            if not callable(cancellation_validator) or not cancellation_validator(
                artifacts
            ):
                raise
        self._validate_outputs(step, artifacts, upstream_artifacts)
        return StepDispatchResult(
            step_id=step.step_id,
            operation=step.operation,
            adapter_id=adapter.adapter_id,
            adapter_version=adapter.adapter_version,
            artifacts=artifacts,
        )

    def dispatch_plan(
        self,
        plan: RuntimeRequestPlan,
        *,
        context: StepDispatchContext | None = None,
    ) -> tuple[StepDispatchResult, ...]:
        """Dispatch a topologically ordered plan once per typed DAG node."""
        outputs: dict[str, tuple[StepOutputArtifact, ...]] = {}
        results: list[StepDispatchResult] = []
        for step in plan.steps:
            unresolved = set(step.depends_on).difference(outputs)
            if unresolved:
                raise StepDispatchError(
                    "plan is not topologically ordered: "
                    + ", ".join(sorted(unresolved))
                )
            upstream = tuple(
                artifact
                for dependency_id in step.depends_on
                for artifact in outputs[dependency_id]
            )
            result = self.dispatch(step, upstream, context=context)
            outputs[step.step_id] = result.artifacts
            results.append(result)
        return tuple(results)

    @staticmethod
    def _validate_upstream(
        step: ConcreteDagStep,
        artifacts: tuple[StepOutputArtifact, ...],
    ) -> None:
        if not step.depends_on:
            if artifacts:
                raise StepDispatchError("entry step received undeclared artifacts")
            return
        if len({item.artifact_id for item in artifacts}) != len(artifacts):
            raise StepDispatchError("step received duplicate upstream artifacts")
        for artifact in artifacts:
            artifact.validate()
            if artifact.producer_step_id not in step.depends_on:
                raise StepDispatchError(
                    "step received artifact from an undeclared dependency"
                )
        expected_contracts = set(step.input_artifact_contract_ids)
        actual_contracts = {item.contract_id for item in artifacts}
        if actual_contracts != expected_contracts:
            raise StepDispatchError("step input artifact contracts do not match")

    @staticmethod
    def _validate_outputs(
        step: ConcreteDagStep,
        artifacts: tuple[StepOutputArtifact, ...],
        upstream_artifacts: tuple[StepOutputArtifact, ...],
    ) -> None:
        if not isinstance(artifacts, tuple):
            raise StepDispatchError("operation adapter must return an artifact tuple")
        if len({item.artifact_id for item in artifacts}) != len(artifacts):
            raise StepDispatchError("operation adapter returned duplicate artifacts")
        expected_contracts = set(step.output_artifact_contract_ids)
        actual_contracts = {item.contract_id for item in artifacts}
        if (
            len(actual_contracts) != len(artifacts)
            or actual_contracts != expected_contracts
        ):
            raise StepDispatchError("operation adapter output contracts do not match")
        expected_dependencies = resolved_input_artifact_ids(
            step,
            upstream_artifacts,
        )
        for artifact in artifacts:
            artifact.validate()
            if artifact.producer_step_id != step.step_id:
                raise StepDispatchError(
                    "step artifact producer identity does not match"
                )
            if artifact.producer_operation is not step.operation:
                raise StepDispatchError(
                    "step artifact producer operation does not match"
                )
            if artifact.artifact.descriptor.dependencies != expected_dependencies:
                raise StepDispatchError(
                    "step artifact dependencies do not match inputs"
                )


def _external_input_artifact_ids(step: ConcreteDagStep) -> tuple[ArtifactID, ...]:
    result: list[ArtifactID] = []
    contracts = set(step.input_artifact_contract_ids)
    if (
        "ingest.source-selection.v1" in contracts
        and step.inputs.source_selection_artifact_id is not None
        and not step.depends_on
    ):
        result.append(step.inputs.source_selection_artifact_id)
    if (
        "ingest.corpus-snapshot.v1" in contracts
        and step.inputs.corpus_id is not None
        and not step.depends_on
    ):
        result.append(step.inputs.corpus_id)
    if (
        {"index.composite.v1", "index.lexical.v1"}.intersection(contracts)
        and step.inputs.index_id is not None
        and not step.depends_on
    ):
        result.append(step.inputs.index_id)
    return tuple(result)


def resolved_input_artifact_ids(
    step: ConcreteDagStep,
    upstream_artifacts: tuple[StepOutputArtifact, ...],
) -> tuple[ArtifactID, ...]:
    """Resolve upstream and external immutable inputs for one concrete step."""
    return tuple(
        sorted(
            {
                *(item.artifact_id for item in upstream_artifacts),
                *_external_input_artifact_ids(step),
            }
        )
    )


__all__ = [
    "OperationAdapter",
    "OperationDispatcher",
    "StepDispatchCancelled",
    "StepDispatchTimedOut",
    "StepDispatchContext",
    "StepDispatchError",
    "StepDispatchResult",
    "StepOutputArtifact",
    "resolved_input_artifact_ids",
]
