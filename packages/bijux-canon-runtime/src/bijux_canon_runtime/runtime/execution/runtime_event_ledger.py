# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Immutable event ledger for typed Runtime step execution."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import Enum, StrEnum
import threading

from bijux_canon_runtime.model.artifact import AddressedArtifact, canonical_json_bytes
from bijux_canon_runtime.model.execution.request_plan import (
    ConcreteDagStep,
    RuntimeRequestPlan,
)
from bijux_canon_runtime.model.execution.run_identity import ExecutionAttemptIdentity
from bijux_canon_runtime.ontology.ids import ArtifactID
from bijux_canon_runtime.runtime.execution.operation_dispatcher import (
    StepOutputArtifact,
)
from bijux_canon_runtime.runtime.persistence.payload_store import (
    DurableArtifactPayloadStore,
)


class RuntimeEventKind(StrEnum):
    """Complete transition vocabulary for Runtime DAG execution."""

    PLANNED = "planned"
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    SKIPPED = "skipped"
    PUBLISHED = "published"


@dataclass(frozen=True, slots=True)
class RuntimeErrorRecord:
    """Exact typed failure retained without losing its causal message."""

    error_type: str
    message: str
    causes: tuple[tuple[str, str], ...]

    @classmethod
    def from_exception(cls, error: Exception) -> RuntimeErrorRecord:
        """Retain the full explicit exception chain without traceback addresses."""
        causes: list[tuple[str, str]] = []
        current = error.__cause__
        seen: set[int] = set()
        while current is not None and id(current) not in seen:
            seen.add(id(current))
            causes.append((type(current).__name__, str(current)))
            current = current.__cause__
        return cls(type(error).__name__, str(error), tuple(causes))


@dataclass(frozen=True, slots=True)
class RuntimeEventRecord:
    """One immutable execution event with complete artifact and policy context."""

    sequence: int
    event_kind: RuntimeEventKind
    run_id: str
    attempt_id: str
    request_id: str
    plan_sha256: str
    step_id: str
    operation: str
    occurred_at: str
    duration_ms: float | None
    declared_input_contract_ids: tuple[str, ...]
    declared_output_contract_ids: tuple[str, ...]
    input_artifact_ids: tuple[str, ...]
    output_artifact_ids: tuple[str, ...]
    check_ids: tuple[str, ...]
    policy: dict[str, object]
    error: RuntimeErrorRecord | None


def _json_value(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_json_value(item) for item in value]
    return value


class RuntimeEventLedger:
    """Hash-chain and persist every planned and observed Runtime transition."""

    def __init__(
        self,
        *,
        store: DurableArtifactPayloadStore,
        plan: RuntimeRequestPlan,
        attempt: ExecutionAttemptIdentity,
        clock: Callable[[], datetime] | None = None,
        execution_metadata: Mapping[str, object] | None = None,
        manifest_dependencies: tuple[ArtifactID, ...] = (),
    ) -> None:
        if plan.request_id != attempt.request_id:
            raise ValueError("event ledger plan and attempt identities do not match")
        self._store = store
        self._plan = plan
        self._attempt = attempt
        self._clock = clock or (lambda: datetime.now(UTC))
        metadata = {} if execution_metadata is None else dict(execution_metadata)
        self._execution_metadata = _json_value(metadata)
        canonical_json_bytes(self._execution_metadata)
        self._records: list[RuntimeEventRecord] = []
        self._artifact_ids: list[ArtifactID] = []
        self._lock = threading.Lock()
        manifest = AddressedArtifact.from_json(
            {
                "attempt": _json_value(asdict(attempt)),
                "execution_metadata": self._execution_metadata,
                "plan": _json_value(asdict(plan)),
                "request_id": str(attempt.request_id),
                "run_id": str(attempt.run_id),
                "schema_version": "bijux.runtime.execution-manifest.v1",
            },
            schema_id="bijux.runtime.execution-manifest.v1",
            producer="bijux-canon-runtime:event-ledger",
            dependencies=tuple(sorted(set(manifest_dependencies))),
        )
        self._store.put(manifest)
        self._manifest_artifact_id = manifest.descriptor.artifact_id

    @property
    def plan_sha256(self) -> str:
        """Return the immutable plan identity owned by this ledger."""
        return self._plan.plan_sha256

    @property
    def records(self) -> tuple[RuntimeEventRecord, ...]:
        """Return events in persisted order."""
        return tuple(self._records)

    @property
    def artifact_ids(self) -> tuple[ArtifactID, ...]:
        """Return the immutable event artifact chain."""
        return tuple(self._artifact_ids)

    @property
    def manifest_artifact_id(self) -> ArtifactID:
        """Return the immutable plan and attempt manifest for inspection."""
        return self._manifest_artifact_id

    @property
    def run_id(self) -> str:
        """Return the authoritative semantic run identity."""
        return str(self._attempt.run_id)

    def record(
        self,
        *,
        step: ConcreteDagStep,
        event_kind: RuntimeEventKind,
        inputs: tuple[StepOutputArtifact, ...] = (),
        outputs: tuple[StepOutputArtifact, ...] = (),
        external_input_artifact_ids: tuple[ArtifactID, ...] = (),
        duration_ms: float | None = None,
        error: Exception | None = None,
    ) -> RuntimeEventRecord:
        """Persist one fully bound step event before execution advances."""
        self._validate_event(event_kind, outputs, duration_ms, error)
        policy = {
            "budget": asdict(step.inputs.budget),
            "execution_profile": step.inputs.execution_profile.value,
            "output_policy": (
                None
                if step.inputs.output_policy is None
                else asdict(step.inputs.output_policy)
            ),
            "replay_mode": step.inputs.replay_mode.value,
            "scope": step.inputs.scope,
            "execution_metadata": self._execution_metadata,
        }
        with self._lock:
            for output in outputs:
                self._store.put(output.artifact)
            record = RuntimeEventRecord(
                sequence=len(self._records),
                event_kind=event_kind,
                run_id=str(self._attempt.run_id),
                attempt_id=self._attempt.attempt_id,
                request_id=str(self._attempt.request_id),
                plan_sha256=self._plan.plan_sha256,
                step_id=step.step_id,
                operation=step.operation.value,
                occurred_at=self._clock().isoformat(),
                duration_ms=duration_ms,
                declared_input_contract_ids=step.input_artifact_contract_ids,
                declared_output_contract_ids=step.output_artifact_contract_ids,
                input_artifact_ids=tuple(
                    str(item)
                    for item in sorted(
                        {
                            *(input_.artifact_id for input_ in inputs),
                            *external_input_artifact_ids,
                        }
                    )
                ),
                output_artifact_ids=tuple(str(item.artifact_id) for item in outputs),
                check_ids=(
                    tuple(f"artifact-contract:{item.contract_id}" for item in outputs)
                    if event_kind
                    in {RuntimeEventKind.COMPLETED, RuntimeEventKind.PUBLISHED}
                    else ()
                ),
                policy=policy,
                error=(
                    None if error is None else RuntimeErrorRecord.from_exception(error)
                ),
            )
            artifact = AddressedArtifact.from_json(
                _json_value(asdict(record)),
                schema_id="bijux.runtime.execution-event.v1",
                producer="bijux-canon-runtime:event-ledger",
                dependencies=tuple(
                    sorted(
                        {
                            self._artifact_ids[-1]
                            if self._artifact_ids
                            else self._manifest_artifact_id,
                            *(item.artifact_id for item in inputs),
                            *external_input_artifact_ids,
                            *(item.artifact_id for item in outputs),
                        }
                    )
                ),
            )
            self._store.put(artifact)
            self._records.append(record)
            self._artifact_ids.append(artifact.descriptor.artifact_id)
            return record

    @staticmethod
    def _validate_event(
        event_kind: RuntimeEventKind,
        outputs: tuple[StepOutputArtifact, ...],
        duration_ms: float | None,
        error: Exception | None,
    ) -> None:
        terminal = {
            RuntimeEventKind.COMPLETED,
            RuntimeEventKind.FAILED,
            RuntimeEventKind.CANCELLED,
            RuntimeEventKind.TIMED_OUT,
            RuntimeEventKind.SKIPPED,
            RuntimeEventKind.PUBLISHED,
        }
        if event_kind in terminal and (duration_ms is None or duration_ms < 0):
            raise ValueError("terminal Runtime events require a duration")
        if event_kind not in terminal and duration_ms is not None:
            raise ValueError("nonterminal Runtime events must not have a duration")
        error_kinds = {
            RuntimeEventKind.FAILED,
            RuntimeEventKind.CANCELLED,
            RuntimeEventKind.TIMED_OUT,
            RuntimeEventKind.SKIPPED,
        }
        if event_kind is RuntimeEventKind.FAILED and error is None:
            raise ValueError("failed Runtime events require an exact error")
        if event_kind not in error_kinds and error is not None:
            raise ValueError("this Runtime event cannot retain an error")
        if outputs and event_kind not in {
            RuntimeEventKind.COMPLETED,
            RuntimeEventKind.PUBLISHED,
        }:
            raise ValueError("only successful Runtime events may retain outputs")


__all__ = [
    "RuntimeErrorRecord",
    "RuntimeEventKind",
    "RuntimeEventLedger",
    "RuntimeEventRecord",
]
