# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Recoverable publication protocol joining durable blobs and metadata."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from bijux_canon_runtime.model.artifact import (
    AddressedArtifact,
    ImmutableArtifactDescriptor,
    canonical_json_bytes,
)
from bijux_canon_runtime.ontology.ids import ArtifactID, ContentHash, RunID, TenantID
from bijux_canon_runtime.runtime.persistence.filesystem_payload_store import (
    AtomicFilesystemArtifactPayloadStore,
)
from bijux_canon_runtime.runtime.persistence.metadata_authority import (
    ArtifactReferenceRecord,
    DuckDBMetadataAuthority,
    MetadataIntegrityError,
    PublicationTransactionRecord,
    ReferenceState,
)


class PublicationRecoveryError(RuntimeError):
    """Raised when a prepared publication cannot be recovered safely."""


@dataclass(frozen=True, slots=True)
class PublicationItem:
    """One logical name and complete immutable payload in a publication."""

    logical_artifact_id: str
    revision: int
    artifact: AddressedArtifact


@dataclass(frozen=True, slots=True)
class PublicationOutcome:
    """Terminal or recoverable state for one publication transaction."""

    transaction_id: str
    status: str
    intent_hash: str
    artifact_ids: tuple[ArtifactID, ...]


class ArtifactPublicationCoordinator:
    """Make durable blobs visible through one recoverable metadata activation."""

    def __init__(
        self,
        *,
        payload_store: AtomicFilesystemArtifactPayloadStore,
        database_path: Path,
    ) -> None:
        self._payload_store = payload_store
        self._database_path = database_path

    def prepare(
        self,
        *,
        tenant_id: TenantID,
        run_id: RunID,
        transaction_id: str,
        items: tuple[PublicationItem, ...],
        created_at: str,
    ) -> PublicationOutcome:
        """Durably publish all blobs, then record their exact activation intent."""
        if not transaction_id.strip() or not items:
            raise ValueError("publication transaction and items must not be empty")
        identities = {
            (item.logical_artifact_id, item.revision) for item in items
        }
        if len(identities) != len(items):
            raise ValueError("publication logical revisions must be unique")
        for item in items:
            for dependency in item.artifact.descriptor.dependencies:
                self._payload_store.load(dependency)
            self._payload_store.put(item.artifact)
            if self._payload_store.load(item.artifact.descriptor.artifact_id) != item.artifact:
                raise PublicationRecoveryError(
                    "durable payload validation changed published content"
                )

        intent_bytes = canonical_json_bytes(
            {
                "items": [self._item_record(item) for item in items],
                "run_id": str(run_id),
                "tenant_id": str(tenant_id),
                "transaction_id": transaction_id,
            }
        )
        intent_hash = hashlib.sha256(intent_bytes).hexdigest()
        with DuckDBMetadataAuthority(self._database_path) as authority:
            transaction = authority.prepare_publication_transaction(
                tenant_id=tenant_id,
                run_id=run_id,
                transaction_id=transaction_id,
                intent_hash=intent_hash,
                intent_json=intent_bytes.decode("utf-8"),
                created_at=created_at,
            )
        return self._outcome(transaction, items)

    def commit(
        self,
        *,
        tenant_id: TenantID,
        run_id: RunID,
        transaction_id: str,
        completed_at: str,
    ) -> PublicationOutcome:
        """Recover a prepared intent and atomically activate its metadata."""
        with DuckDBMetadataAuthority(self._database_path) as authority:
            transaction = authority.publication_transaction(
                tenant_id=tenant_id,
                run_id=run_id,
                transaction_id=transaction_id,
            )
            assert transaction is not None
            if transaction.status == "aborted":
                raise PublicationRecoveryError("publication transaction is aborted")
            try:
                items = self._items_from_transaction(transaction)
                for item in items:
                    loaded = self._payload_store.load(
                        item.artifact.descriptor.artifact_id
                    )
                    if loaded != item.artifact:
                        raise PublicationRecoveryError(
                            "durable payload does not match prepared intent"
                        )
                    authority.register_payload(
                        loaded.descriptor,
                        created_at=transaction.created_at,
                    )
            except (
                KeyError,
                MetadataIntegrityError,
                PublicationRecoveryError,
                ValueError,
            ) as exc:
                authority.abort_prepared_publication(
                    transaction=transaction,
                    failure_reason="durable payload unavailable or invalid",
                    completed_at=completed_at,
                )
                raise PublicationRecoveryError(
                    "prepared publication failed durable payload validation"
                ) from exc
            references = tuple(
                ArtifactReferenceRecord(
                    tenant_id=tenant_id,
                    run_id=run_id,
                    logical_artifact_id=item.logical_artifact_id,
                    revision=item.revision,
                    target_artifact_id=item.artifact.descriptor.artifact_id,
                    reference_state=ReferenceState.ACTIVE,
                    created_at=transaction.created_at,
                )
                for item in items
            )
            try:
                committed = authority.commit_prepared_publication(
                    transaction=transaction,
                    references=references,
                    completed_at=completed_at,
                )
            except MetadataIntegrityError as exc:
                authority.abort_prepared_publication(
                    transaction=transaction,
                    failure_reason="publication activation violated metadata integrity",
                    completed_at=completed_at,
                )
                raise PublicationRecoveryError(
                    "prepared publication could not be activated"
                ) from exc
        return self._outcome(committed, items)

    def publish(
        self,
        *,
        tenant_id: TenantID,
        run_id: RunID,
        transaction_id: str,
        items: tuple[PublicationItem, ...],
        created_at: str,
        completed_at: str,
    ) -> PublicationOutcome:
        """Prepare and commit one idempotent publication transaction."""
        self.prepare(
            tenant_id=tenant_id,
            run_id=run_id,
            transaction_id=transaction_id,
            items=items,
            created_at=created_at,
        )
        return self.commit(
            tenant_id=tenant_id,
            run_id=run_id,
            transaction_id=transaction_id,
            completed_at=completed_at,
        )

    def _items_from_transaction(
        self, transaction: PublicationTransactionRecord
    ) -> tuple[PublicationItem, ...]:
        intent_bytes = transaction.intent_json.encode("utf-8")
        if hashlib.sha256(intent_bytes).hexdigest() != transaction.intent_hash:
            raise PublicationRecoveryError("publication intent hash does not match")
        try:
            intent = json.loads(intent_bytes)
            if (
                not isinstance(intent, dict)
                or intent.get("tenant_id") != str(transaction.tenant_id)
                or intent.get("run_id") != str(transaction.run_id)
                or intent.get("transaction_id") != transaction.transaction_id
                or not isinstance(intent.get("items"), list)
            ):
                raise ValueError("publication intent shape is invalid")
            return tuple(self._item_from_record(item) for item in intent["items"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise PublicationRecoveryError("publication intent cannot be decoded") from exc

    def _item_from_record(self, record: Any) -> PublicationItem:
        if not isinstance(record, dict):
            raise ValueError("publication item must be an object")
        descriptor_record = record["descriptor"]
        if not isinstance(descriptor_record, dict):
            raise ValueError("publication descriptor must be an object")
        dependencies = descriptor_record["dependencies"]
        if not isinstance(dependencies, list):
            raise ValueError("publication dependencies must be a list")
        descriptor = ImmutableArtifactDescriptor(
            artifact_id=ArtifactID(descriptor_record["artifact_id"]),
            schema_id=descriptor_record["schema_id"],
            media_type=descriptor_record["media_type"],
            size_bytes=descriptor_record["size_bytes"],
            payload_sha256=ContentHash(descriptor_record["payload_sha256"]),
            producer=descriptor_record["producer"],
            dependencies=tuple(ArtifactID(item) for item in dependencies),
        )
        artifact = self._payload_store.load(descriptor.artifact_id)
        if artifact.descriptor != descriptor:
            raise ValueError("publication descriptor does not match durable payload")
        return PublicationItem(
            logical_artifact_id=record["logical_artifact_id"],
            revision=record["revision"],
            artifact=artifact,
        )

    @staticmethod
    def _item_record(item: PublicationItem) -> dict[str, object]:
        descriptor = item.artifact.descriptor
        return {
            "descriptor": {
                "artifact_id": str(descriptor.artifact_id),
                "dependencies": [str(value) for value in descriptor.dependencies],
                "media_type": descriptor.media_type,
                "payload_sha256": str(descriptor.payload_sha256),
                "producer": descriptor.producer,
                "schema_id": descriptor.schema_id,
                "size_bytes": descriptor.size_bytes,
            },
            "logical_artifact_id": item.logical_artifact_id,
            "revision": item.revision,
        }

    @staticmethod
    def _outcome(
        transaction: PublicationTransactionRecord,
        items: tuple[PublicationItem, ...],
    ) -> PublicationOutcome:
        return PublicationOutcome(
            transaction_id=transaction.transaction_id,
            status=transaction.status,
            intent_hash=transaction.intent_hash,
            artifact_ids=tuple(
                item.artifact.descriptor.artifact_id for item in items
            ),
        )


__all__ = [
    "ArtifactPublicationCoordinator",
    "PublicationItem",
    "PublicationOutcome",
    "PublicationRecoveryError",
]
