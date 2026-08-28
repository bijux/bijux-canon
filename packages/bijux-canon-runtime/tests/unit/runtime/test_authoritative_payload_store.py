# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
import shutil

import pytest

from bijux_canon_runtime.model.artifact import AddressedArtifact
from bijux_canon_runtime.observability.storage.execution_store import (
    DuckDBExecutionStore,
)
from bijux_canon_runtime.ontology.ids import ArtifactID
from bijux_canon_runtime.runtime.persistence.authoritative_payload_store import (
    AuthoritativeArtifactPayloadStore,
)
from bijux_canon_runtime.runtime.persistence.filesystem_payload_store import (
    AtomicFilesystemArtifactPayloadStore,
)
from bijux_canon_runtime.runtime.persistence.metadata_authority import (
    DuckDBMetadataAuthority,
    MetadataIntegrityError,
)


def _store(
    tmp_path: Path,
) -> tuple[
    AtomicFilesystemArtifactPayloadStore,
    AuthoritativeArtifactPayloadStore,
    Path,
]:
    database_path = tmp_path / "runtime.duckdb"
    database = DuckDBExecutionStore(database_path)
    database.close()
    filesystem = AtomicFilesystemArtifactPayloadStore(tmp_path / "cas")
    return (
        filesystem,
        AuthoritativeArtifactPayloadStore(
            payload_store=filesystem,
            database_path=database_path,
        ),
        database_path,
    )


def test_prior_cas_inventory_is_registered_in_dependency_order(
    tmp_path: Path,
) -> None:
    filesystem, authority_store, database_path = _store(tmp_path)
    source = AddressedArtifact.from_json(
        {"content": "observed evidence"},
        schema_id="test.source.v1",
        producer="test:source",
    )
    answer = AddressedArtifact.from_json(
        {"claim": "grounded result"},
        schema_id="test.answer.v1",
        producer="test:answer",
        dependencies=(source.descriptor.artifact_id,),
    )
    filesystem.put(source)
    filesystem.put(answer)

    assert authority_store.reconcile_inventory() == 2
    assert authority_store.reconcile_inventory() == 0
    with DuckDBMetadataAuthority(database_path) as authority:
        assert authority.payload_ids() == {
            source.descriptor.artifact_id,
            answer.descriptor.artifact_id,
        }


def test_metadata_never_points_to_a_failed_cas_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    filesystem, authority_store, database_path = _store(tmp_path)
    artifact = AddressedArtifact.from_json(
        {"content": "complete bytes"},
        schema_id="test.failure.v1",
        producer="test:failure",
    )

    def refuse_registration(*_args: object, **_kwargs: object) -> None:
        raise MetadataIntegrityError("injected metadata failure")

    monkeypatch.setattr(
        DuckDBMetadataAuthority,
        "register_payload",
        refuse_registration,
    )
    with pytest.raises(MetadataIntegrityError, match="injected metadata failure"):
        authority_store.put(artifact)

    assert filesystem.load(artifact.descriptor.artifact_id) == artifact
    with DuckDBMetadataAuthority(database_path) as authority:
        assert authority.payload_ids() == frozenset()


def test_reconciliation_refuses_metadata_whose_cas_bytes_are_absent(
    tmp_path: Path,
) -> None:
    filesystem, authority_store, _database_path = _store(tmp_path)
    artifact = AddressedArtifact.from_json(
        {"content": "durable"},
        schema_id="test.integrity.v1",
        producer="test:integrity",
    )
    authority_store.put(artifact)
    digest = str(artifact.descriptor.artifact_id).removeprefix("sha256:")
    shutil.rmtree(filesystem.root / "objects" / "sha256" / digest[:2] / digest)

    with pytest.raises(
        MetadataIntegrityError,
        match="points to absent CAS content",
    ):
        authority_store.reconcile_inventory()


def test_reconciliation_leases_metadata_before_snapshotting_cas(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    filesystem, authority_store, _database_path = _store(tmp_path)
    events: list[str] = []
    original_enter = DuckDBMetadataAuthority.__enter__
    original_inventory = filesystem.iter_artifact_ids

    def enter(authority: DuckDBMetadataAuthority) -> DuckDBMetadataAuthority:
        events.append("metadata-leased")
        return original_enter(authority)

    def inventory() -> Iterator[ArtifactID]:
        events.append("cas-snapshotted")
        yield from original_inventory()

    monkeypatch.setattr(DuckDBMetadataAuthority, "__enter__", enter)
    monkeypatch.setattr(filesystem, "iter_artifact_ids", inventory)

    assert authority_store.reconcile_inventory() == 0
    assert events == ["metadata-leased", "cas-snapshotted"]
