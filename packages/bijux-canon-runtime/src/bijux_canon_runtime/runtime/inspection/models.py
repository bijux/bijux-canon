# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Typed values returned by restart-safe Runtime inspection."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from bijux_canon_runtime.ontology.ids import ArtifactID


class RuntimeInspectionError(RuntimeError):
    """Persisted Runtime state is missing, ambiguous, or internally invalid."""


@dataclass(frozen=True, slots=True)
class RuntimeInspectionLimits:
    """Hard memory and cardinality limits for restart-safe inspection."""

    max_inventory_artifacts: int = 100_000
    max_control_artifacts: int = 20_000
    max_related_artifacts: int = 20_000
    max_loaded_payload_bytes: int = 512 * 1024 * 1024

    def __post_init__(self) -> None:
        if (
            min(
                self.max_inventory_artifacts,
                self.max_control_artifacts,
                self.max_related_artifacts,
                self.max_loaded_payload_bytes,
            )
            < 1
        ):
            raise ValueError("Runtime inspection limits must be positive")


class InspectedRunStatus(StrEnum):
    """Status derived exclusively from persisted step events."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


class InspectedStepStatus(StrEnum):
    """Most advanced persisted state for one plan step."""

    PLANNED = "planned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    SKIPPED = "skipped"


class InspectedEventKind(StrEnum):
    """Persisted execution-event kinds accepted by inspection."""

    PLANNED = "planned"
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    SKIPPED = "skipped"
    PUBLISHED = "published"


@dataclass(frozen=True, slots=True)
class InspectedErrorRecord:
    """Exact persisted failure and its explicit causal chain."""

    error_type: str
    message: str
    causes: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class InspectedAttempt:
    """One immutable execution attempt and its explicit lineage."""

    attempt_id: str
    attempt_number: int
    relation: str
    request_id: str
    source_attempt_id: str | None
    supersedes_attempt_id: str | None
    retry_id: str | None
    replay_id: str | None
    process_id: str
    manifest_artifact_id: ArtifactID


@dataclass(frozen=True, slots=True)
class InspectedEvent:
    """One verified event and the artifact that durably contains it."""

    artifact_id: ArtifactID
    sequence: int
    event_kind: InspectedEventKind
    step_id: str
    operation: str
    occurred_at: str
    duration_ms: float | None
    declared_input_contract_ids: tuple[str, ...]
    declared_output_contract_ids: tuple[str, ...]
    input_artifact_ids: tuple[ArtifactID, ...]
    output_artifact_ids: tuple[ArtifactID, ...]
    check_ids: tuple[str, ...]
    policy: dict[str, object]
    error: InspectedErrorRecord | None


@dataclass(frozen=True, slots=True)
class InspectedDagStep:
    """One exact plan node joined to its latest persisted execution state."""

    step_id: str
    operation: str
    depends_on: tuple[str, ...]
    input_contract_ids: tuple[str, ...]
    output_contract_ids: tuple[str, ...]
    status: InspectedStepStatus
    attempt_id: str
    input_artifact_ids: tuple[ArtifactID, ...]
    output_artifact_ids: tuple[ArtifactID, ...]
    error: InspectedErrorRecord | None


@dataclass(frozen=True, slots=True)
class InspectedArtifact:
    """Verified immutable artifact metadata and its JSON value when applicable."""

    artifact_id: ArtifactID
    schema_id: str
    media_type: str
    payload_sha256: str
    size_bytes: int
    producer: str
    dependency_artifact_ids: tuple[ArtifactID, ...]
    json_value: object | None


@dataclass(frozen=True, slots=True)
class InspectedArtifactPayloadPage:
    """One deliberate bounded page of immutable artifact payload bytes."""

    schema_version: str
    artifact_id: ArtifactID
    media_type: str
    payload_sha256: str
    total_bytes: int
    offset: int
    byte_length: int
    data_base64: str
    next_offset: int | None


@dataclass(frozen=True, slots=True)
class PersistedInspectionValue:
    """A semantic value resolved to its exact persisted source location."""

    source_artifact_id: ArtifactID
    source_step_id: str | None
    json_path: str
    value: object


@dataclass(frozen=True, slots=True)
class InspectedFailure:
    """A failure joined to the exact step and event that retained it."""

    event_artifact_id: ArtifactID
    event_sequence: int
    step_id: str
    error: InspectedErrorRecord


@dataclass(frozen=True, slots=True)
class RuntimeRunInspection:
    """Complete restart-safe view of one selected attempt and run lineage."""

    schema_version: str
    run_id: str
    request_id: str
    selected_attempt_id: str
    status: InspectedRunStatus
    plan_sha256: str
    request_operation: str
    entry_step_ids: tuple[str, ...]
    terminal_step_ids: tuple[str, ...]
    attempts: tuple[InspectedAttempt, ...]
    steps: tuple[InspectedDagStep, ...]
    events: tuple[InspectedEvent, ...]
    artifacts: tuple[InspectedArtifact, ...]
    queries: tuple[PersistedInspectionValue, ...]
    hits: tuple[PersistedInspectionValue, ...]
    claims: tuple[PersistedInspectionValue, ...]
    citations: tuple[PersistedInspectionValue, ...]
    tool_calls: tuple[PersistedInspectionValue, ...]
    provider_calls: tuple[PersistedInspectionValue, ...]
    budgets: tuple[PersistedInspectionValue, ...]
    checks: tuple[PersistedInspectionValue, ...]
    failures: tuple[InspectedFailure, ...]


__all__ = [
    "InspectedArtifact",
    "InspectedArtifactPayloadPage",
    "InspectedAttempt",
    "InspectedDagStep",
    "InspectedErrorRecord",
    "InspectedEvent",
    "InspectedEventKind",
    "InspectedFailure",
    "InspectedRunStatus",
    "InspectedStepStatus",
    "PersistedInspectionValue",
    "RuntimeInspectionError",
    "RuntimeInspectionLimits",
    "RuntimeRunInspection",
]
