# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Integrity validation for persisted Runtime inspection state."""

from __future__ import annotations

from collections.abc import Iterable
import hashlib

from bijux_canon_runtime.model.artifact import canonical_json_bytes
from bijux_canon_runtime.ontology.ids import ArtifactID
from bijux_canon_runtime.runtime.inspection.models import (
    InspectedArtifact,
    InspectedAttempt,
    InspectedDagStep,
    InspectedErrorRecord,
    InspectedEvent,
    InspectedEventKind,
    InspectedRunStatus,
    InspectedStepStatus,
    RuntimeInspectionError,
)
from bijux_canon_runtime.runtime.inspection.parsing import (
    optional_string,
    required_dict,
    required_integer,
    required_list,
    required_object,
    required_string,
    required_string_list,
    required_strings,
)


def parse_attempt(
    *,
    manifest_payload: dict[str, object],
    attempt: dict[str, object],
    manifest_artifact_id: ArtifactID,
) -> InspectedAttempt:
    """Validate and reconstruct one attempt identity."""
    attempt_id = required_string(attempt, "attempt_id")
    run_id = required_string(attempt, "run_id")
    request_id = required_string(attempt, "request_id")
    if run_id != required_string(manifest_payload, "run_id"):
        raise RuntimeInspectionError("attempt run identity does not match manifest")
    if request_id != required_string(manifest_payload, "request_id"):
        raise RuntimeInspectionError("attempt request identity does not match manifest")
    attempt_number = required_integer(attempt, "attempt_number")
    if attempt_number < 1:
        raise RuntimeInspectionError("execution attempt number must be positive")
    relation = required_string(attempt, "relation")
    source_attempt_id = optional_string(attempt, "source_attempt_id")
    lineage = {
        "attempt_number": attempt_number,
        "relation": relation,
        "request_id": request_id,
        "run_id": run_id,
        "schema_version": "bijux.runtime.execution-attempt.v1",
        "source_attempt_id": source_attempt_id,
    }
    digest = hashlib.sha256(canonical_json_bytes(lineage)).hexdigest()
    if attempt_id != f"attempt_v1_{digest}":
        raise RuntimeInspectionError("execution attempt identity is invalid")
    retry_id = optional_string(attempt, "retry_id")
    replay_id = optional_string(attempt, "replay_id")
    if retry_id != (f"retry_v1_{digest}" if relation == "retry" else None):
        raise RuntimeInspectionError("retry identity does not match attempt relation")
    if replay_id != (f"replay_v1_{digest}" if relation == "replay" else None):
        raise RuntimeInspectionError("replay identity does not match attempt relation")
    return InspectedAttempt(
        attempt_id=attempt_id,
        attempt_number=attempt_number,
        relation=relation,
        request_id=request_id,
        source_attempt_id=source_attempt_id,
        supersedes_attempt_id=optional_string(attempt, "supersedes_attempt_id"),
        retry_id=retry_id,
        replay_id=replay_id,
        process_id=required_string(attempt, "process_id"),
        manifest_artifact_id=manifest_artifact_id,
    )


def validate_attempt_lineage(attempts: tuple[InspectedAttempt, ...]) -> None:
    """Require a contiguous, fully resolved attempt lineage."""
    numbers = [item.attempt_number for item in attempts]
    if numbers != list(range(1, len(numbers) + 1)):
        raise RuntimeInspectionError("run attempt numbers are not contiguous")
    by_id = {item.attempt_id: item for item in attempts}
    for attempt in attempts:
        if attempt.attempt_number == 1:
            if attempt.relation != "initial" or attempt.source_attempt_id is not None:
                raise RuntimeInspectionError("initial attempt lineage is invalid")
            continue
        source = by_id.get(attempt.source_attempt_id or "")
        if (
            attempt.relation not in {"retry", "replay"}
            or source is None
            or source.attempt_number + 1 != attempt.attempt_number
            or attempt.supersedes_attempt_id != attempt.source_attempt_id
        ):
            raise RuntimeInspectionError("derived attempt lineage is unresolved")


def validate_plan(plan: dict[str, object]) -> None:
    """Validate plan hash, DAG boundaries, edges, contracts, and acyclicity."""
    plan_hash = required_string(plan, "plan_sha256")
    hash_payload = {key: value for key, value in plan.items() if key != "plan_sha256"}
    expected = hashlib.sha256(canonical_json_bytes(hash_payload)).hexdigest()
    if plan_hash != expected:
        raise RuntimeInspectionError("persisted Runtime plan hash is invalid")
    raw_steps = required_list(plan, "steps")
    steps = tuple(required_dict(item, "plan step") for item in raw_steps)
    step_ids = tuple(required_string(item, "step_id") for item in steps)
    if len(step_ids) != len(set(step_ids)):
        raise RuntimeInspectionError("persisted Runtime plan has duplicate steps")
    by_id = dict(zip(step_ids, steps, strict=True))
    actual_entries = tuple(
        step_id
        for step_id in step_ids
        if not required_strings(by_id[step_id], "depends_on")
    )
    depended_on = {
        dependency
        for step in steps
        for dependency in required_strings(step, "depends_on")
    }
    actual_terminals = tuple(
        step_id for step_id in step_ids if step_id not in depended_on
    )
    if (
        required_strings(plan, "entry_step_ids") != actual_entries
        or required_strings(plan, "terminal_step_ids") != actual_terminals
    ):
        raise RuntimeInspectionError("persisted Runtime DAG boundaries are invalid")
    resolved: set[str] = set()
    remaining = set(step_ids)
    while remaining:
        ready = {
            step_id
            for step_id in remaining
            if set(required_strings(by_id[step_id], "depends_on")).issubset(resolved)
        }
        if not ready:
            raise RuntimeInspectionError("persisted Runtime plan is cyclic")
        remaining.difference_update(ready)
        resolved.update(ready)
    for step_id, step in by_id.items():
        for dependency_id in required_strings(step, "depends_on"):
            dependency = by_id.get(dependency_id)
            if dependency is None:
                raise RuntimeInspectionError("persisted Runtime DAG edge is unresolved")
            inputs = set(required_strings(step, "input_artifact_contract_ids"))
            outputs = set(required_strings(dependency, "output_artifact_contract_ids"))
            if not inputs.intersection(outputs):
                raise RuntimeInspectionError(
                    f"persisted Runtime DAG edge into {step_id} has no contract"
                )


def parse_event(
    artifact_id: ArtifactID,
    payload: dict[str, object],
) -> InspectedEvent:
    """Validate and reconstruct one persisted execution event."""
    raw_error = payload.get("error")
    error = None
    if raw_error is not None:
        error_record = required_dict(raw_error, "event error")
        causes_list: list[tuple[str, str]] = []
        for item in required_list(error_record, "causes"):
            cause = required_string_list(item, "event error cause")
            if len(cause) != 2:
                raise RuntimeInspectionError("event error cause is invalid")
            causes_list.append((cause[0], cause[1]))
        error = InspectedErrorRecord(
            required_string(error_record, "error_type"),
            required_string(error_record, "message", permit_empty=True),
            tuple(causes_list),
        )
    duration = payload.get("duration_ms")
    if duration is not None and (
        isinstance(duration, bool) or not isinstance(duration, int | float)
    ):
        raise RuntimeInspectionError("event duration is invalid")
    return InspectedEvent(
        artifact_id=artifact_id,
        sequence=required_integer(payload, "sequence"),
        event_kind=InspectedEventKind(required_string(payload, "event_kind")),
        step_id=required_string(payload, "step_id"),
        operation=required_string(payload, "operation"),
        occurred_at=required_string(payload, "occurred_at"),
        duration_ms=None if duration is None else float(duration),
        declared_input_contract_ids=required_strings(
            payload, "declared_input_contract_ids"
        ),
        declared_output_contract_ids=required_strings(
            payload, "declared_output_contract_ids"
        ),
        input_artifact_ids=tuple(
            ArtifactID(item) for item in required_strings(payload, "input_artifact_ids")
        ),
        output_artifact_ids=tuple(
            ArtifactID(item)
            for item in required_strings(payload, "output_artifact_ids")
        ),
        check_ids=required_strings(payload, "check_ids"),
        policy=required_object(payload, "policy"),
        error=error,
    )


def build_steps(
    plan: dict[str, object],
    attempt_id: str,
    events: tuple[InspectedEvent, ...],
) -> tuple[InspectedDagStep, ...]:
    """Join exact plan nodes to validated event lifecycles."""
    by_step: dict[str, list[InspectedEvent]] = {}
    for event in events:
        by_step.setdefault(event.step_id, []).append(event)
    raw_steps = required_list(plan, "steps")
    declared_step_ids = {
        required_string(required_dict(item, "plan step"), "step_id")
        for item in raw_steps
    }
    if not set(by_step).issubset(declared_step_ids):
        raise RuntimeInspectionError("execution events name an undeclared step")
    result: list[InspectedDagStep] = []
    for raw_step in raw_steps:
        step = required_dict(raw_step, "plan step")
        step_id = required_string(step, "step_id")
        step_events = by_step.get(step_id, [])
        if (
            not step_events
            or step_events[0].event_kind is not InspectedEventKind.PLANNED
        ):
            raise RuntimeInspectionError("plan step has no initial planned event")
        operation = required_string(step, "operation")
        input_contracts = required_strings(step, "input_artifact_contract_ids")
        output_contracts = required_strings(step, "output_artifact_contract_ids")
        if any(
            event.operation != operation
            or event.declared_input_contract_ids != input_contracts
            or event.declared_output_contract_ids != output_contracts
            for event in step_events
        ):
            raise RuntimeInspectionError("step event contract is inconsistent")
        kinds = tuple(event.event_kind for event in step_events)
        if kinds not in _VALID_EVENT_SEQUENCES or (
            InspectedEventKind.PUBLISHED in kinds and operation != "publish"
        ):
            raise RuntimeInspectionError("step event lifecycle is invalid")
        latest = step_events[-1]
        result.append(
            InspectedDagStep(
                step_id=step_id,
                operation=operation,
                depends_on=required_strings(step, "depends_on"),
                input_contract_ids=input_contracts,
                output_contract_ids=output_contracts,
                status=_EVENT_STATUSES[latest.event_kind],
                attempt_id=attempt_id,
                input_artifact_ids=_ordered_artifact_ids(
                    event.input_artifact_ids for event in step_events
                ),
                output_artifact_ids=_ordered_artifact_ids(
                    event.output_artifact_ids for event in step_events
                ),
                error=latest.error,
            )
        )
    return tuple(result)


def validate_artifact_contracts(
    steps: tuple[InspectedDagStep, ...],
    artifacts: tuple[InspectedArtifact, ...],
) -> None:
    """Require every observed step artifact to satisfy its declared contract."""
    by_id = {item.artifact_id: item for item in artifacts}
    for step in steps:
        try:
            outputs = tuple(by_id[item] for item in step.output_artifact_ids)
            inputs = tuple(by_id[item] for item in step.input_artifact_ids)
        except KeyError as exc:
            raise RuntimeInspectionError(
                "step artifact is absent from the resolved graph"
            ) from exc
        if outputs and {item.schema_id for item in outputs} != set(
            step.output_contract_ids
        ):
            raise RuntimeInspectionError("step output artifact contract is invalid")
        if (
            step.depends_on
            and (
                step.status
                in {
                    InspectedStepStatus.RUNNING,
                    InspectedStepStatus.COMPLETED,
                    InspectedStepStatus.FAILED,
                }
                or (
                    step.status is InspectedStepStatus.TIMED_OUT
                    and bool(step.input_artifact_ids)
                )
            )
            and {item.schema_id for item in inputs} != set(step.input_contract_ids)
        ):
            raise RuntimeInspectionError("step input artifact contract is invalid")


def run_status(steps: tuple[InspectedDagStep, ...]) -> InspectedRunStatus:
    """Derive the run outcome from complete step state."""
    statuses = {step.status for step in steps}
    if InspectedStepStatus.FAILED in statuses:
        return InspectedRunStatus.FAILED
    if InspectedStepStatus.TIMED_OUT in statuses:
        return InspectedRunStatus.TIMED_OUT
    if InspectedStepStatus.CANCELLED in statuses:
        return InspectedRunStatus.CANCELLED
    if InspectedStepStatus.SKIPPED in statuses:
        return InspectedRunStatus.FAILED
    if statuses == {InspectedStepStatus.COMPLETED}:
        return InspectedRunStatus.COMPLETED
    return InspectedRunStatus.RUNNING


def _ordered_artifact_ids(
    groups: Iterable[tuple[ArtifactID, ...]],
) -> tuple[ArtifactID, ...]:
    ordered: dict[ArtifactID, None] = {}
    for group in groups:
        for artifact_id in group:
            ordered.setdefault(artifact_id, None)
    return tuple(ordered)


_EVENT_STATUSES = {
    InspectedEventKind.PLANNED: InspectedStepStatus.PLANNED,
    InspectedEventKind.STARTED: InspectedStepStatus.RUNNING,
    InspectedEventKind.COMPLETED: InspectedStepStatus.COMPLETED,
    InspectedEventKind.PUBLISHED: InspectedStepStatus.COMPLETED,
    InspectedEventKind.FAILED: InspectedStepStatus.FAILED,
    InspectedEventKind.CANCELLED: InspectedStepStatus.CANCELLED,
    InspectedEventKind.TIMED_OUT: InspectedStepStatus.TIMED_OUT,
    InspectedEventKind.SKIPPED: InspectedStepStatus.SKIPPED,
}

_VALID_EVENT_SEQUENCES = {
    (InspectedEventKind.PLANNED,),
    (InspectedEventKind.PLANNED, InspectedEventKind.STARTED),
    (InspectedEventKind.PLANNED, InspectedEventKind.CANCELLED),
    (InspectedEventKind.PLANNED, InspectedEventKind.TIMED_OUT),
    (InspectedEventKind.PLANNED, InspectedEventKind.SKIPPED),
    (
        InspectedEventKind.PLANNED,
        InspectedEventKind.STARTED,
        InspectedEventKind.COMPLETED,
    ),
    (
        InspectedEventKind.PLANNED,
        InspectedEventKind.STARTED,
        InspectedEventKind.FAILED,
    ),
    (
        InspectedEventKind.PLANNED,
        InspectedEventKind.STARTED,
        InspectedEventKind.CANCELLED,
    ),
    (
        InspectedEventKind.PLANNED,
        InspectedEventKind.STARTED,
        InspectedEventKind.TIMED_OUT,
    ),
    (
        InspectedEventKind.PLANNED,
        InspectedEventKind.STARTED,
        InspectedEventKind.COMPLETED,
        InspectedEventKind.PUBLISHED,
    ),
}


__all__ = [
    "build_steps",
    "parse_attempt",
    "parse_event",
    "run_status",
    "validate_artifact_contracts",
    "validate_attempt_lineage",
    "validate_plan",
]
