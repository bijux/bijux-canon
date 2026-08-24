# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Restart-safe orchestration for persisted Runtime inspection."""

from __future__ import annotations

from dataclasses import dataclass
import base64
import json

from bijux_canon_runtime.model.artifact import AddressedArtifact
from bijux_canon_runtime.ontology.ids import ArtifactID
from bijux_canon_runtime.runtime.inspection.models import (
    InspectedArtifact,
    InspectedArtifactPayloadPage,
    InspectedAttempt,
    InspectedEvent,
    InspectedFailure,
    PersistedInspectionValue,
    RuntimeInspectionError,
    RuntimeInspectionLimits,
    RuntimeRunInspection,
)
from bijux_canon_runtime.runtime.inspection.parsing import (
    json_object,
    required_object,
    required_string,
    required_strings,
)
from bijux_canon_runtime.runtime.inspection.semantic_values import (
    extract_semantics,
    plan_values,
)
from bijux_canon_runtime.runtime.inspection.validation import (
    build_steps,
    parse_attempt,
    parse_event,
    run_status,
    validate_artifact_contracts,
    validate_attempt_lineage,
    validate_plan,
)
from bijux_canon_runtime.runtime.persistence.filesystem_payload_store import (
    PayloadCorruptionError,
)
from bijux_canon_runtime.runtime.persistence.payload_store import (
    DurableArtifactPayloadStore,
)


@dataclass(frozen=True, slots=True)
class _Manifest:
    artifact_id: ArtifactID
    payload: dict[str, object]
    plan: dict[str, object]
    attempt: dict[str, object]


_DEFAULT_RUNTIME_INSPECTION_LIMITS = RuntimeInspectionLimits()


class RuntimeRunInspector:
    """Reconstruct a run from an atomic payload store after process restart."""

    def __init__(
        self,
        store: DurableArtifactPayloadStore,
        *,
        limits: RuntimeInspectionLimits = _DEFAULT_RUNTIME_INSPECTION_LIMITS,
    ) -> None:
        self._store = store
        self._limits = limits

    def inspect(
        self,
        run_id: str,
        *,
        attempt_id: str | None = None,
    ) -> RuntimeRunInspection:
        """Resolve and validate one persisted attempt plus all run lineage."""
        if not run_id.strip():
            raise ValueError("inspection run identity must not be empty")
        inventory = self._control_inventory()
        manifests = self._manifests(inventory, run_id)
        if not manifests:
            raise KeyError(f"persisted Runtime run not found: {run_id}")
        attempts = tuple(
            sorted(
                (self._attempt(item) for item in manifests),
                key=lambda item: (item.attempt_number, item.attempt_id),
            )
        )
        validate_attempt_lineage(attempts)
        selected = self._select_manifest(manifests, attempts, attempt_id)
        selected_attempt = self._attempt(selected)
        plan = selected.plan
        validate_plan(plan)
        if required_string(plan, "request_id") != selected_attempt.request_id:
            raise RuntimeInspectionError("plan request identity does not match attempt")
        events = self._events(
            inventory,
            run_id=run_id,
            attempt_id=selected_attempt.attempt_id,
            request_id=selected_attempt.request_id,
            plan_sha256=required_string(plan, "plan_sha256"),
            manifest_artifact_id=selected.artifact_id,
        )
        steps = build_steps(plan, selected_attempt.attempt_id, events)
        related = self._related_artifacts(selected.artifact_id, events)
        artifacts = tuple(self._artifact(item) for item in related)
        validate_artifact_contracts(steps, artifacts)
        output_steps = {
            artifact_id: event.step_id
            for event in events
            for artifact_id in event.output_artifact_ids
        }
        semantics = extract_semantics(artifacts, output_steps)
        queries = plan_values(
            manifest_artifact_id=selected.artifact_id,
            plan=plan,
            field_name="query",
        )
        budgets = plan_values(
            manifest_artifact_id=selected.artifact_id,
            plan=plan,
            field_name="budget",
        )
        checks = list(semantics["checks"])
        for event in events:
            checks.extend(
                PersistedInspectionValue(
                    event.artifact_id,
                    event.step_id,
                    f"$.check_ids[{index}]",
                    check_id,
                )
                for index, check_id in enumerate(event.check_ids)
            )
        failures = tuple(
            InspectedFailure(
                event.artifact_id,
                event.sequence,
                event.step_id,
                event.error,
            )
            for event in events
            if event.error is not None
        )
        return RuntimeRunInspection(
            schema_version="bijux.runtime.run-inspection.v1",
            run_id=run_id,
            request_id=required_string(selected.payload, "request_id"),
            selected_attempt_id=selected_attempt.attempt_id,
            status=run_status(steps),
            plan_sha256=required_string(plan, "plan_sha256"),
            request_operation=required_string(plan, "request_operation"),
            entry_step_ids=required_strings(plan, "entry_step_ids"),
            terminal_step_ids=required_strings(plan, "terminal_step_ids"),
            attempts=attempts,
            steps=steps,
            events=events,
            artifacts=artifacts,
            queries=queries,
            hits=semantics["hits"],
            claims=semantics["claims"],
            citations=semantics["citations"],
            tool_calls=semantics["tool_calls"],
            provider_calls=semantics["provider_calls"],
            budgets=budgets,
            checks=tuple(checks),
            failures=failures,
        )

    def read_artifact_payload_page(
        self,
        artifact_id: ArtifactID,
        *,
        offset: int = 0,
        max_bytes: int = 64 * 1024,
    ) -> InspectedArtifactPayloadPage:
        """Return one checksum-bound payload page without expanding it as JSON."""
        if offset < 0:
            raise ValueError("artifact payload offset must not be negative")
        if not 1 <= max_bytes <= 64 * 1024:
            raise ValueError("artifact payload max_bytes must be between 1 and 65536")
        artifact = self._store.load(artifact_id)
        payload = artifact.canonical_bytes
        if offset > len(payload):
            raise ValueError("artifact payload offset exceeds payload size")
        page = payload[offset : offset + max_bytes]
        next_offset = offset + len(page) if offset + len(page) < len(payload) else None
        descriptor = artifact.descriptor
        return InspectedArtifactPayloadPage(
            schema_version="bijux.runtime.artifact-payload-page.v1",
            artifact_id=descriptor.artifact_id,
            media_type=descriptor.media_type,
            payload_sha256=str(descriptor.payload_sha256),
            total_bytes=len(payload),
            offset=offset,
            byte_length=len(page),
            data_base64=base64.b64encode(page).decode("ascii"),
            next_offset=next_offset,
        )

    def _control_inventory(
        self,
    ) -> tuple[tuple[ArtifactID, AddressedArtifact], ...]:
        inventory: list[tuple[ArtifactID, AddressedArtifact]] = []
        loaded_bytes = 0
        for index, artifact_id in enumerate(self._store.iter_artifact_ids(), start=1):
            if index > self._limits.max_inventory_artifacts:
                raise RuntimeInspectionError(
                    "artifact inventory exceeds the configured inspection limit"
                )
            try:
                artifact = self._store.load(artifact_id)
            except (KeyError, PayloadCorruptionError, ValueError):
                continue
            if artifact.descriptor.schema_id not in {
                "bijux.runtime.execution-manifest.v1",
                "bijux.runtime.execution-event.v1",
            }:
                continue
            inventory.append((artifact_id, artifact))
            loaded_bytes += artifact.descriptor.size_bytes
            if (
                len(inventory) > self._limits.max_control_artifacts
                or loaded_bytes > self._limits.max_loaded_payload_bytes
            ):
                raise RuntimeInspectionError(
                    "Runtime control artifacts exceed configured inspection limits"
                )
        return tuple(inventory)

    def _manifests(
        self,
        inventory: tuple[tuple[ArtifactID, AddressedArtifact], ...],
        run_id: str,
    ) -> tuple[_Manifest, ...]:
        manifests: list[_Manifest] = []
        seen_attempts: set[str] = set()
        for artifact_id, artifact in inventory:
            if artifact.descriptor.schema_id != "bijux.runtime.execution-manifest.v1":
                continue
            payload = json_object(artifact)
            if payload.get("run_id") != run_id:
                continue
            if payload.get("schema_version") != artifact.descriptor.schema_id:
                raise RuntimeInspectionError(
                    "execution manifest schema is inconsistent"
                )
            plan = required_object(payload, "plan")
            attempt = required_object(payload, "attempt")
            attempt_id = required_string(attempt, "attempt_id")
            if attempt_id in seen_attempts:
                raise RuntimeInspectionError("execution attempt has multiple manifests")
            seen_attempts.add(attempt_id)
            manifests.append(_Manifest(artifact_id, payload, plan, attempt))
        return tuple(manifests)

    @staticmethod
    def _attempt(manifest: _Manifest) -> InspectedAttempt:
        return parse_attempt(
            manifest_payload=manifest.payload,
            attempt=manifest.attempt,
            manifest_artifact_id=manifest.artifact_id,
        )

    @staticmethod
    def _select_manifest(
        manifests: tuple[_Manifest, ...],
        attempts: tuple[InspectedAttempt, ...],
        attempt_id: str | None,
    ) -> _Manifest:
        selected_id = attempts[-1].attempt_id if attempt_id is None else attempt_id
        for manifest in manifests:
            if required_string(manifest.attempt, "attempt_id") == selected_id:
                return manifest
        raise KeyError(f"persisted Runtime attempt not found: {selected_id}")

    def _events(
        self,
        inventory: tuple[tuple[ArtifactID, AddressedArtifact], ...],
        *,
        run_id: str,
        attempt_id: str,
        request_id: str,
        plan_sha256: str,
        manifest_artifact_id: ArtifactID,
    ) -> tuple[InspectedEvent, ...]:
        located: list[tuple[InspectedEvent, AddressedArtifact]] = []
        for artifact_id, artifact in inventory:
            if artifact.descriptor.schema_id != "bijux.runtime.execution-event.v1":
                continue
            payload = json_object(artifact)
            if (
                payload.get("run_id") != run_id
                or payload.get("attempt_id") != attempt_id
            ):
                continue
            if payload.get("request_id") != request_id:
                raise RuntimeInspectionError("event request identity is inconsistent")
            if payload.get("plan_sha256") != plan_sha256:
                raise RuntimeInspectionError("event belongs to another Runtime plan")
            located.append((parse_event(artifact_id, payload), artifact))
        located.sort(key=lambda item: item[0].sequence)
        if not located:
            raise RuntimeInspectionError("execution attempt has no persisted events")
        if [event.sequence for event, _ in located] != list(range(len(located))):
            raise RuntimeInspectionError("execution event sequence is not contiguous")
        previous = manifest_artifact_id
        for event, artifact in located:
            if previous not in artifact.descriptor.dependencies:
                raise RuntimeInspectionError("execution event chain is broken")
            previous = event.artifact_id
        return tuple(event for event, _ in located)

    def _related_artifacts(
        self,
        manifest_artifact_id: ArtifactID,
        events: tuple[InspectedEvent, ...],
    ) -> tuple[AddressedArtifact, ...]:
        pending = {
            manifest_artifact_id,
            *(event.artifact_id for event in events),
            *(item for event in events for item in event.input_artifact_ids),
            *(item for event in events for item in event.output_artifact_ids),
        }
        loaded: dict[ArtifactID, AddressedArtifact] = {}
        loaded_bytes = 0
        while pending:
            artifact_id = pending.pop()
            if artifact_id in loaded:
                continue
            try:
                artifact = self._store.load(artifact_id)
            except (KeyError, PayloadCorruptionError, ValueError) as exc:
                raise RuntimeInspectionError(
                    f"run references an unavailable artifact: {artifact_id}"
                ) from exc
            loaded[artifact_id] = artifact
            loaded_bytes += artifact.descriptor.size_bytes
            if (
                len(loaded) > self._limits.max_related_artifacts
                or loaded_bytes > self._limits.max_loaded_payload_bytes
            ):
                raise RuntimeInspectionError(
                    "run lineage exceeds configured inspection limits"
                )
            pending.update(artifact.descriptor.dependencies)
        return tuple(loaded[item] for item in sorted(loaded))

    @staticmethod
    def _artifact(artifact: AddressedArtifact) -> InspectedArtifact:
        json_value: object | None = None
        if artifact.descriptor.media_type == "application/json":
            try:
                json_value = json.loads(artifact.canonical_bytes)
            except json.JSONDecodeError as exc:
                raise RuntimeInspectionError(
                    "JSON artifact contains an invalid payload"
                ) from exc
        descriptor = artifact.descriptor
        return InspectedArtifact(
            artifact_id=descriptor.artifact_id,
            schema_id=descriptor.schema_id,
            media_type=descriptor.media_type,
            payload_sha256=str(descriptor.payload_sha256),
            size_bytes=descriptor.size_bytes,
            producer=descriptor.producer,
            dependency_artifact_ids=descriptor.dependencies,
            json_value=json_value,
        )


__all__ = ["RuntimeRunInspector"]
