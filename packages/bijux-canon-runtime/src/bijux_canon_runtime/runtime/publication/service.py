# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Publish complete run identities as content-addressed receipts."""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import threading

from bijux_canon_runtime.model.artifact import AddressedArtifact, canonical_json_bytes
from bijux_canon_runtime.observability.storage.execution_store_lock import (
    acquire_execution_store_lock,
)
from bijux_canon_runtime.ontology.ids import ArtifactID
from bijux_canon_runtime.runtime.inspection import (
    InspectedAttempt,
    InspectedRunStatus,
    RuntimeRunInspection,
    RuntimeRunInspector,
)
from bijux_canon_runtime.runtime.persistence.filesystem_payload_store import (
    AtomicFilesystemArtifactPayloadStore,
)
from bijux_canon_runtime.runtime.publication.models import (
    ReplayPublicationDisposition,
    ReplayPublicationStatus,
    RunPublicationBindings,
    RuntimeRunPublicationError,
    RuntimeRunPublicationOutcome,
)

_RECEIPT_SCHEMA = "bijux.runtime.run-publication-receipt.v1"
_PRODUCER = "bijux-canon-runtime:run-receipt"
_PROCESS_LOCKS: dict[Path, threading.Lock] = {}
_PROCESS_LOCKS_GUARD = threading.Lock()


def _process_lock(path: Path) -> threading.Lock:
    with _PROCESS_LOCKS_GUARD:
        return _PROCESS_LOCKS.setdefault(path.resolve(), threading.Lock())


class RuntimeRunReceiptPublisher:
    """Create idempotent, path-independent receipts from persisted attempts."""

    def __init__(
        self,
        store: AtomicFilesystemArtifactPayloadStore,
        *,
        lock_timeout_seconds: float = 5.0,
    ) -> None:
        if lock_timeout_seconds < 0:
            raise ValueError("publication lock timeout must be non-negative")
        self._store = store
        self._inspector = RuntimeRunInspector(store)
        self._lock_timeout_seconds = lock_timeout_seconds
        self._process_lock = _process_lock(self._store.root / ".run-publications.lock")

    def publish(
        self,
        *,
        run_id: str,
        selected_attempt_id: str,
        bindings: RunPublicationBindings,
        replay: ReplayPublicationStatus,
        limitations: tuple[str, ...] = (),
    ) -> RuntimeRunPublicationOutcome:
        """Validate and publish one immutable revision after restart."""
        with (
            self._process_lock,
            acquire_execution_store_lock(
                self._store.root / ".run-publications.lock",
                timeout_seconds=self._lock_timeout_seconds,
            ),
        ):
            return self._publish(
                run_id=run_id,
                selected_attempt_id=selected_attempt_id,
                bindings=bindings,
                replay=replay,
                limitations=limitations,
            )

    def _publish(
        self,
        *,
        run_id: str,
        selected_attempt_id: str,
        bindings: RunPublicationBindings,
        replay: ReplayPublicationStatus,
        limitations: tuple[str, ...],
    ) -> RuntimeRunPublicationOutcome:
        self._validate_limitations(limitations)
        inspection = self._inspector.inspect(
            run_id,
            attempt_id=selected_attempt_id,
        )
        if inspection.status is not InspectedRunStatus.COMPLETED:
            raise RuntimeRunPublicationError(
                "only a completed Runtime attempt can be published"
            )
        selected = next(
            item
            for item in inspection.attempts
            if item.attempt_id == selected_attempt_id
        )
        self._validate_replay(inspection, selected, replay)
        request_record = self._request_record(
            inspection,
            selected,
            bindings,
            replay,
            limitations,
        )
        request_sha256 = hashlib.sha256(
            canonical_json_bytes(request_record)
        ).hexdigest()
        existing = self._receipts(run_id)
        reused = next(
            (
                item
                for item in existing
                if item[1].get("publication_request_sha256") == request_sha256
            ),
            None,
        )
        if reused is not None:
            return self._outcome(reused[0], reused[1], reused=True)
        revision = 1 + max(
            (self._integer(item, "revision") for _, item in existing),
            default=0,
        )
        previous_receipt_id = (
            None
            if not existing
            else max(existing, key=lambda item: self._integer(item[1], "revision"))[0]
        )
        publication_id = self._publication_id(
            run_id=run_id,
            selected_attempt_id=selected_attempt_id,
            revision=revision,
            previous_receipt_id=previous_receipt_id,
            request_sha256=request_sha256,
        )
        stable_citation = f"urn:bijux:canon:{run_id}:{publication_id}"
        receipt_record = {
            **request_record,
            "previous_receipt_artifact_id": (
                None if previous_receipt_id is None else str(previous_receipt_id)
            ),
            "publication_id": publication_id,
            "publication_request_sha256": request_sha256,
            "revision": revision,
            "schema_version": _RECEIPT_SCHEMA,
            "stable_citation": stable_citation,
        }
        dependencies = tuple(
            sorted(
                {
                    *(item.artifact_id for item in inspection.artifacts),
                    *(
                        (previous_receipt_id,)
                        if previous_receipt_id is not None
                        else ()
                    ),
                }
            )
        )
        artifact = AddressedArtifact.from_json(
            receipt_record,
            schema_id=_RECEIPT_SCHEMA,
            producer=_PRODUCER,
            dependencies=dependencies,
        )
        self._store.put(artifact)
        persisted = self._store.load(artifact.descriptor.artifact_id)
        if persisted != artifact:
            raise RuntimeRunPublicationError("published receipt failed CAS validation")
        return self._outcome(
            artifact.descriptor.artifact_id,
            receipt_record,
            reused=False,
        )

    def _request_record(
        self,
        inspection: RuntimeRunInspection,
        selected: InspectedAttempt,
        bindings: RunPublicationBindings,
        replay: ReplayPublicationStatus,
        limitations: tuple[str, ...],
    ) -> dict[str, object]:
        artifacts = [
            {
                "artifact_id": str(item.artifact_id),
                "dependencies": [str(value) for value in item.dependency_artifact_ids],
                "media_type": item.media_type,
                "payload_sha256": item.payload_sha256,
                "producer": item.producer,
                "schema_id": item.schema_id,
                "size_bytes": item.size_bytes,
            }
            for item in sorted(
                inspection.artifacts,
                key=lambda value: str(value.artifact_id),
            )
        ]
        checks = [
            {
                "check": item.value,
                "json_path": item.json_path,
                "source_artifact_id": str(item.source_artifact_id),
                "source_step_id": item.source_step_id,
            }
            for item in sorted(
                inspection.checks,
                key=lambda value: (
                    str(value.source_artifact_id),
                    value.json_path,
                ),
            )
        ]
        return {
            "artifact_manifest": artifacts,
            "artifact_manifest_sha256": hashlib.sha256(
                canonical_json_bytes(artifacts)
            ).hexdigest(),
            "bindings": {key: str(value) for key, value in asdict(bindings).items()},
            "checks": checks,
            "checks_sha256": hashlib.sha256(canonical_json_bytes(checks)).hexdigest(),
            "limitations": list(limitations),
            "plan_sha256": inspection.plan_sha256,
            "replay": {
                key: value.value if hasattr(value, "value") else value
                for key, value in asdict(replay).items()
            },
            "request_id": inspection.request_id,
            "run_id": inspection.run_id,
            "selected_attempt": {
                key: str(value) if value is not None else None
                for key, value in asdict(selected).items()
            },
        }

    def _receipts(
        self,
        run_id: str,
    ) -> tuple[tuple[ArtifactID, dict[str, object]], ...]:
        receipts: list[tuple[ArtifactID, dict[str, object]]] = []
        for artifact_id in self._store.artifact_ids():
            artifact = self._store.load(artifact_id)
            if artifact.descriptor.schema_id != _RECEIPT_SCHEMA:
                continue
            try:
                value = json.loads(artifact.canonical_bytes)
            except json.JSONDecodeError as exc:
                raise RuntimeRunPublicationError(
                    "persisted publication receipt is invalid JSON"
                ) from exc
            if not isinstance(value, dict):
                raise RuntimeRunPublicationError(
                    "persisted publication receipt must be an object"
                )
            if value.get("run_id") == run_id:
                receipts.append((artifact_id, value))
        ordered = tuple(
            sorted(receipts, key=lambda item: self._integer(item[1], "revision"))
        )
        if [self._integer(item, "revision") for _, item in ordered] != list(
            range(1, len(ordered) + 1)
        ):
            raise RuntimeRunPublicationError(
                "publication receipt revisions are forked or incomplete"
            )
        previous: ArtifactID | None = None
        for artifact_id, record in ordered:
            if record.get("previous_receipt_artifact_id") != (
                None if previous is None else str(previous)
            ):
                raise RuntimeRunPublicationError(
                    "publication receipt lineage is broken"
                )
            previous = artifact_id
        return ordered

    @staticmethod
    def _validate_replay(
        inspection: RuntimeRunInspection,
        selected: InspectedAttempt,
        replay: ReplayPublicationStatus,
    ) -> None:
        if replay.disposition is ReplayPublicationDisposition.NOT_REQUESTED:
            return
        attempts = {item.attempt_id: item for item in inspection.attempts}
        replay_attempt = attempts.get(replay.replay_attempt_id or "")
        if (
            replay_attempt is None
            or replay_attempt.relation != "replay"
            or replay_attempt.source_attempt_id != replay.source_attempt_id
            or selected.attempt_id != replay_attempt.attempt_id
        ):
            raise RuntimeRunPublicationError(
                "publication replay lineage does not match persisted attempts"
            )

    @staticmethod
    def _validate_limitations(limitations: tuple[str, ...]) -> None:
        if any(not item.strip() or item != item.strip() for item in limitations):
            raise ValueError("publication limitations must be normalized text")
        if len(set(limitations)) != len(limitations):
            raise ValueError("publication limitations must be unique")

    @staticmethod
    def _publication_id(
        *,
        run_id: str,
        selected_attempt_id: str,
        revision: int,
        previous_receipt_id: ArtifactID | None,
        request_sha256: str,
    ) -> str:
        payload = {
            "previous_receipt_artifact_id": (
                None if previous_receipt_id is None else str(previous_receipt_id)
            ),
            "request_sha256": request_sha256,
            "revision": revision,
            "run_id": run_id,
            "schema_version": "bijux.runtime.run-publication-identity.v1",
            "selected_attempt_id": selected_attempt_id,
        }
        digest = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
        return f"publication_v1_{digest}"

    @staticmethod
    def _integer(record: dict[str, object], key: str) -> int:
        value = record.get(key)
        if isinstance(value, bool) or not isinstance(value, int):
            raise RuntimeRunPublicationError(f"receipt {key} must be an integer")
        return value

    @staticmethod
    def _outcome(
        artifact_id: ArtifactID,
        record: dict[str, object],
        *,
        reused: bool,
    ) -> RuntimeRunPublicationOutcome:
        manifest = record.get("artifact_manifest")
        checks = record.get("checks")
        selected = record.get("selected_attempt")
        if (
            not isinstance(manifest, list)
            or not isinstance(checks, list)
            or not isinstance(selected, dict)
        ):
            raise RuntimeRunPublicationError("receipt outcome fields are invalid")
        values = {
            key: record.get(key)
            for key in ("publication_id", "revision", "stable_citation")
        }
        if (
            not isinstance(values["publication_id"], str)
            or not isinstance(values["revision"], int)
            or not isinstance(values["stable_citation"], str)
            or not isinstance(selected.get("attempt_id"), str)
        ):
            raise RuntimeRunPublicationError("receipt identity fields are invalid")
        return RuntimeRunPublicationOutcome(
            publication_id=values["publication_id"],
            revision=values["revision"],
            receipt_artifact_id=artifact_id,
            stable_citation=values["stable_citation"],
            selected_attempt_id=selected["attempt_id"],
            artifact_count=len(manifest),
            check_count=len(checks),
            reused=reused,
        )


__all__ = ["RuntimeRunReceiptPublisher"]
