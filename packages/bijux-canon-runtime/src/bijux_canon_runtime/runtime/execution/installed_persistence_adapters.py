# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Installed persistence manifests and local publication receipts."""

from __future__ import annotations

import json

from bijux_canon_runtime.model.artifact import AddressedArtifact, canonical_json_bytes
from bijux_canon_runtime.model.execution.request_plan import (
    ConcreteDagStep,
    DagOperation,
)
from bijux_canon_runtime.ontology.ids import ArtifactID
from bijux_canon_runtime.runtime.execution.installed_operation_adapters import (
    _bounded_output,
    _json_object,
)
from bijux_canon_runtime.runtime.execution.operation_dispatcher import (
    StepDispatchContext,
    StepDispatchError,
    StepOutputArtifact,
)
from bijux_canon_runtime.runtime.persistence.payload_store import ArtifactPayloadStore


def _required_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise StepDispatchError(f"persistence field is invalid: {field}")
    return value


def _lineage(
    store: ArtifactPayloadStore,
    seeds: tuple[AddressedArtifact, ...],
) -> list[dict[str, object]]:
    artifacts = {item.descriptor.artifact_id: item for item in seeds}
    pending = [
        dependency
        for item in seeds
        for dependency in item.descriptor.dependencies
        if dependency not in artifacts
    ]
    while pending:
        artifact_id = pending.pop()
        if artifact_id in artifacts:
            continue
        try:
            artifact = store.load(artifact_id)
        except (KeyError, ValueError) as error:
            raise StepDispatchError(
                f"persistence lineage artifact is unavailable: {artifact_id}"
            ) from error
        artifacts[artifact_id] = artifact
        pending.extend(
            dependency
            for dependency in artifact.descriptor.dependencies
            if dependency not in artifacts
        )
    return [
        {
            "artifact_id": str(artifact.descriptor.artifact_id),
            "dependencies": [str(item) for item in artifact.descriptor.dependencies],
            "media_type": artifact.descriptor.media_type,
            "payload_sha256": str(artifact.descriptor.payload_sha256),
            "producer": artifact.descriptor.producer,
            "schema_id": artifact.descriptor.schema_id,
            "size_bytes": artifact.descriptor.size_bytes,
        }
        for _, artifact in sorted(artifacts.items(), key=lambda item: str(item[0]))
    ]


def _subject_owned_artifacts(
    store: ArtifactPayloadStore,
    subject: AddressedArtifact,
) -> tuple[AddressedArtifact, ...]:
    if subject.descriptor.schema_id != "agent.research-trace.v1":
        return ()
    try:
        record = json.loads(subject.canonical_bytes)
        raw_artifact_ids = record["counterevidence_retrieval_artifact_ids"]
        if not isinstance(raw_artifact_ids, list):
            raise TypeError
        artifact_ids = tuple(
            ArtifactID(item) for item in raw_artifact_ids if isinstance(item, str)
        )
        if len(artifact_ids) != len(raw_artifact_ids):
            raise TypeError
        return tuple(store.load(artifact_id) for artifact_id in artifact_ids)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise StepDispatchError(
            "research-owned retrieval artifacts are unavailable"
        ) from error


class CanonicalPersistenceOperationAdapter:
    """Close a verified subject over its complete reachable CAS lineage."""

    adapter_id = "bijux-canon-runtime:run-manifest:v1"
    adapter_version = "1.0"
    operation = DagOperation.PERSIST

    def __init__(self, *, store: ArtifactPayloadStore) -> None:
        self._store = store

    def execute(
        self,
        step: ConcreteDagStep,
        upstream_artifacts: tuple[StepOutputArtifact, ...],
        context: StepDispatchContext,
    ) -> tuple[StepOutputArtifact, ...]:
        context.raise_if_stopped()
        if len(upstream_artifacts) != 1:
            raise StepDispatchError("persistence requires one verification receipt")
        receipt_artifact = upstream_artifacts[0].artifact
        receipt = _json_object(
            receipt_artifact,
            "reason.verification-receipt.v1",
        )
        if (
            receipt.get("schema_version")
            != "bijux.canon.reason.verification_receipt.v1"
            or receipt.get("status") != "verified"
        ):
            raise StepDispatchError("persistence requires a verified receipt")
        subject_id = ArtifactID(
            _required_string(receipt.get("subject_artifact_id"), "subject_artifact_id")
        )
        try:
            subject = self._store.load(subject_id)
        except (KeyError, ValueError) as error:
            raise StepDispatchError(
                "verified subject is unavailable in Runtime CAS"
            ) from error
        if subject.descriptor.schema_id != _required_string(
            receipt.get("subject_contract_id"), "subject_contract_id"
        ) or str(subject.descriptor.payload_sha256) != _required_string(
            receipt.get("subject_payload_sha256"), "subject_payload_sha256"
        ):
            raise StepDispatchError(
                "verification receipt does not match stored subject"
            )
        owned_artifacts = _subject_owned_artifacts(self._store, subject)
        lineage = _lineage(
            self._store,
            (subject, receipt_artifact, *owned_artifacts),
        )
        payload = canonical_json_bytes(
            {
                "artifact_count": len(lineage),
                "artifacts": lineage,
                "request_id": str(step.inputs.request_id),
                "request_operation": step.inputs.request_operation.value,
                "schema_version": "bijux.canon.runtime.run_manifest.v1",
                "status": "persisted",
                "subject_artifact_id": str(subject_id),
                "verification_receipt_artifact_id": str(
                    receipt_artifact.descriptor.artifact_id
                ),
            }
        )
        context.raise_if_stopped()
        return _bounded_output(
            step=step,
            contract_id="runtime.run-manifest.v1",
            media_type="application/json",
            payload=payload,
            upstream=upstream_artifacts,
        )


class CanonicalPublicationOperationAdapter:
    """Publish a verified manifest through the local content-addressed surface."""

    adapter_id = "bijux-canon-runtime:local-publication:v1"
    adapter_version = "1.0"
    operation = DagOperation.PUBLISH

    def execute(
        self,
        step: ConcreteDagStep,
        upstream_artifacts: tuple[StepOutputArtifact, ...],
        context: StepDispatchContext,
    ) -> tuple[StepOutputArtifact, ...]:
        context.raise_if_stopped()
        if len(upstream_artifacts) != 1:
            raise StepDispatchError("publication requires one persisted run manifest")
        if step.inputs.output_policy is None:
            raise StepDispatchError("publication requires an output policy")
        manifest_artifact = upstream_artifacts[0].artifact
        manifest = _json_object(manifest_artifact, "runtime.run-manifest.v1")
        if (
            manifest.get("schema_version") != "bijux.canon.runtime.run_manifest.v1"
            or manifest.get("status") != "persisted"
        ):
            raise StepDispatchError("publication requires a persisted run manifest")
        payload = canonical_json_bytes(
            {
                "manifest_artifact_id": str(manifest_artifact.descriptor.artifact_id),
                "publication_surface": "runtime-cas",
                "schema_version": "bijux.canon.runtime.publication_receipt.v1",
                "status": (
                    "published-local"
                    if step.inputs.output_policy.publish
                    else "not-requested"
                ),
                "subject_artifact_id": _required_string(
                    manifest.get("subject_artifact_id"), "subject_artifact_id"
                ),
            }
        )
        context.raise_if_stopped()
        return _bounded_output(
            step=step,
            contract_id="runtime.publication-receipt.v1",
            media_type="application/json",
            payload=payload,
            upstream=upstream_artifacts,
        )


__all__ = [
    "CanonicalPersistenceOperationAdapter",
    "CanonicalPublicationOperationAdapter",
]
