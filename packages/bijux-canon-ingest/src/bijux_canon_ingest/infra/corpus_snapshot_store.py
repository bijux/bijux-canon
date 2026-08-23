# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Crash-safe filesystem publication for canonical corpus snapshots."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import uuid
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from enum import StrEnum
from pathlib import Path
from typing import Final

from bijux_canon_ingest.domain.corpus_publication import (
    PublishedCorpusSnapshot,
    SnapshotRecovery,
)
from bijux_canon_ingest.domain.corpus_snapshot import CorpusSnapshot

ACTIVE_MANIFEST: Final = "active.json"
PREVIOUS_MANIFEST: Final = "previous.json"
GENERATION_MANIFEST: Final = "manifest.json"
SNAPSHOT_DOCUMENT: Final = "snapshot.json"
RELATION_DOCUMENT: Final = "relation.json"


class PublicationCheckpoint(StrEnum):
    """Stable fault-injection boundaries in manifest-last publication."""

    layout_ready = "layout_ready"
    objects_staged = "objects_staged"
    relation_staged = "relation_staged"
    objects_persisted = "objects_persisted"
    relation_persisted = "relation_persisted"
    generation_persisted = "generation_persisted"
    previous_pointer_persisted = "previous_pointer_persisted"
    before_activation = "before_activation"


PublicationFaultHook = Callable[[PublicationCheckpoint], None]


class SnapshotPublicationError(RuntimeError):
    """A stored generation or activation manifest failed validation."""


def _canonical_json(value: object) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError:
        if os.name == "nt":
            return
        raise
    try:
        try:
            os.fsync(descriptor)
        except OSError:
            if os.name != "nt":
                raise
    finally:
        os.close(descriptor)


def _write_new(path: Path, content: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


class CorpusSnapshotStore:
    """Publish immutable generations and atomically activate their manifests."""

    def __init__(
        self,
        root: str | Path,
        *,
        fault_hook: PublicationFaultHook | None = None,
    ) -> None:
        self.root = Path(root)
        self.generations = self.root / "generations"
        self.staging = self.root / "staging"
        self.objects = self.root / "objects"
        self.relations = self.root / "relations"
        self.lock_path = self.root / "publication.lock"
        self._fault_hook = fault_hook

    def _checkpoint(self, checkpoint: PublicationCheckpoint) -> None:
        if self._fault_hook is not None:
            self._fault_hook(checkpoint)

    @staticmethod
    def _ensure_directory(path: Path, *, parents: bool = False) -> None:
        if path.is_symlink() or (path.exists() and not path.is_dir()):
            raise SnapshotPublicationError(
                f"snapshot publication directory is unsafe: {path.name}"
            )
        path.mkdir(parents=parents, exist_ok=True)

    def _ensure_layout(self) -> None:
        self._ensure_directory(self.root, parents=True)
        for path in (self.generations, self.staging, self.objects, self.relations):
            self._ensure_directory(path)
        _fsync_directory(self.root)

    @contextmanager
    def _writer_lock(self) -> Iterator[None]:
        if self.lock_path.is_symlink() or (
            self.lock_path.exists() and not self.lock_path.is_file()
        ):
            raise SnapshotPublicationError("snapshot publication lock is unsafe")
        with self.lock_path.open("a+b") as stream:
            if os.name == "nt":  # pragma: no cover - Windows release lane
                import msvcrt

                msvcrt.locking(  # type: ignore[attr-defined]
                    stream.fileno(),
                    msvcrt.LK_LOCK,  # type: ignore[attr-defined]
                    1,
                )
            else:
                import fcntl

                fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                if os.name == "nt":  # pragma: no cover - Windows release lane
                    import msvcrt

                    stream.seek(0)
                    msvcrt.locking(  # type: ignore[attr-defined]
                        stream.fileno(),
                        msvcrt.LK_UNLCK,  # type: ignore[attr-defined]
                        1,
                    )
                else:
                    import fcntl

                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)

    def _atomic_write(self, destination: Path, content: bytes) -> None:
        staged = self.staging / f"activation-{uuid.uuid4().hex}.json"
        try:
            _write_new(staged, content)
            os.replace(staged, destination)
            _fsync_directory(destination.parent)
        finally:
            staged.unlink(missing_ok=True)

    @staticmethod
    def _object_entry(
        *,
        content: bytes,
        kind: str,
        document_id: str | None,
        domain_identity: str,
        ordinal: int | None = None,
    ) -> dict[str, object]:
        return {
            "byte_length": len(content),
            "document_id": document_id,
            "domain_identity": domain_identity,
            "kind": kind,
            "object_sha256": hashlib.sha256(content).hexdigest(),
            "ordinal": ordinal,
        }

    def _snapshot_relation(
        self,
        snapshot: CorpusSnapshot,
    ) -> tuple[dict[str, object], dict[str, bytes], int, int]:
        entries: list[dict[str, object]] = []
        objects: dict[str, bytes] = {}

        def register(
            content: bytes,
            *,
            kind: str,
            document_id: str | None,
            domain_identity: str,
            ordinal: int | None = None,
        ) -> None:
            entry = self._object_entry(
                content=content,
                kind=kind,
                document_id=document_id,
                domain_identity=domain_identity,
                ordinal=ordinal,
            )
            digest = str(entry["object_sha256"])
            existing = objects.get(digest)
            if existing is not None and existing != content:
                raise SnapshotPublicationError("content-addressed object collision")
            objects[digest] = content
            entries.append(entry)

        register(
            snapshot.canonical_bytes,
            kind="snapshot",
            document_id=None,
            domain_identity=snapshot.snapshot_id,
        )
        source_count = 0
        for snapshot_document in snapshot.documents:
            source = snapshot_document.admission.source
            source_path = source.filesystem_path
            if source_path.is_symlink() or not source_path.is_file():
                raise SnapshotPublicationError(
                    "snapshot source is unavailable for immutable publication"
                )
            try:
                source_content = source_path.read_bytes()
            except OSError as error:
                raise SnapshotPublicationError(
                    "snapshot source is unreadable for immutable publication"
                ) from error
            if (
                len(source_content) != source.byte_length
                or hashlib.sha256(source_content).hexdigest() != source.content_sha256
            ):
                raise SnapshotPublicationError(
                    "snapshot source changed before immutable publication"
                )
            register(
                source_content,
                kind="source-bytes",
                document_id=snapshot_document.document_id,
                domain_identity=f"sha256:{source.content_sha256}",
            )
            source_count += 1
            document_manifest = snapshot_document.document.manifest()
            metadata_manifest = snapshot_document.metadata.manifest()
            derived: tuple[tuple[str, Mapping[str, object], str, int | None], ...] = (
                (
                    "parsed-document",
                    document_manifest,
                    str(document_manifest["manifest_sha256"]),
                    None,
                ),
                (
                    "source-metadata",
                    metadata_manifest,
                    str(metadata_manifest["manifest_sha256"]),
                    None,
                ),
                (
                    "citation-lineage",
                    snapshot_document.citation_lineage.manifest(),
                    snapshot_document.citation_lineage.lineage_sha256,
                    None,
                ),
            )
            for kind, manifest, identity, ordinal in derived:
                register(
                    _canonical_json(manifest),
                    kind=kind,
                    document_id=snapshot_document.document_id,
                    domain_identity=identity,
                    ordinal=ordinal,
                )
            for mapping in snapshot_document.mappings:
                register(
                    _canonical_json(mapping.manifest()),
                    kind="normalized-mapping",
                    document_id=snapshot_document.document_id,
                    domain_identity=mapping.mapping_sha256,
                )
            for chunk in snapshot_document.chunks:
                register(
                    _canonical_json(chunk.manifest()),
                    kind="semantic-chunk",
                    document_id=snapshot_document.document_id,
                    domain_identity=chunk.chunk_id,
                    ordinal=chunk.chunk_index,
                )

        def entry_order(item: Mapping[str, object]) -> tuple[str, str, int, str]:
            ordinal = item["ordinal"]
            return (
                str(item["kind"]),
                "" if item["document_id"] is None else str(item["document_id"]),
                ordinal
                if isinstance(ordinal, int) and not isinstance(ordinal, bool)
                else -1,
                str(item["domain_identity"]),
            )

        entries.sort(key=entry_order)
        derived_count = len(entries) - source_count
        relation_payload: dict[str, object] = {
            "derived_object_count": derived_count,
            "objects": entries,
            "schema_version": "bijux.canon.ingest.corpus_object_relation.v1",
            "snapshot_id": snapshot.snapshot_id,
            "source_object_count": source_count,
        }
        relation_sha256 = hashlib.sha256(
            _canonical_json(relation_payload)[:-1]
        ).hexdigest()
        relation = {
            "relation_sha256": f"sha256:{relation_sha256}",
            **relation_payload,
        }
        return relation, objects, source_count, derived_count

    def _publication(
        self,
        snapshot: CorpusSnapshot,
        *,
        relation_sha256: str,
        source_object_count: int,
        derived_object_count: int,
    ) -> PublishedCorpusSnapshot:
        content = snapshot.canonical_bytes
        return PublishedCorpusSnapshot(
            snapshot_id=snapshot.snapshot_id,
            canonical_bytes=content,
            canonical_sha256=hashlib.sha256(content).hexdigest(),
            relation_sha256=relation_sha256,
            source_object_count=source_object_count,
            derived_object_count=derived_object_count,
        )

    def _object_path(self, digest: str) -> Path:
        return self.objects / digest[:2] / digest[2:]

    def _read_relation(
        self,
        manifest: Mapping[str, object],
    ) -> dict[str, object]:
        generation_name = str(manifest["generation_name"])
        path = self.relations / f"{generation_name}.json"
        if path.is_symlink() or not path.is_file():
            raise SnapshotPublicationError("snapshot object relation is unavailable")
        try:
            content = path.read_bytes()
            relation = json.loads(content)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise SnapshotPublicationError(
                "snapshot object relation is unreadable"
            ) from error
        if (
            not isinstance(relation, dict)
            or _canonical_json(relation) != content
            or relation.get("schema_version")
            != "bijux.canon.ingest.corpus_object_relation.v1"
            or relation.get("snapshot_id") != manifest["snapshot_id"]
            or relation.get("relation_sha256") != manifest["relation_sha256"]
            or relation.get("source_object_count") != manifest["source_object_count"]
            or relation.get("derived_object_count") != manifest["derived_object_count"]
        ):
            raise SnapshotPublicationError("snapshot object relation is invalid")
        payload = dict(relation)
        relation_id = payload.pop("relation_sha256", None)
        expected_id = (
            f"sha256:{hashlib.sha256(_canonical_json(payload)[:-1]).hexdigest()}"
        )
        if relation_id != expected_id:
            raise SnapshotPublicationError(
                "snapshot object relation identity is invalid"
            )
        entries = relation.get("objects")
        if not isinstance(entries, list) or not entries:
            raise SnapshotPublicationError("snapshot object relation is empty")
        source_count = 0
        derived_count = 0
        for entry in entries:
            if not isinstance(entry, dict) or set(entry) != {
                "byte_length",
                "document_id",
                "domain_identity",
                "kind",
                "object_sha256",
                "ordinal",
            }:
                raise SnapshotPublicationError(
                    "snapshot object relation entry is invalid"
                )
            digest = entry["object_sha256"]
            byte_length = entry["byte_length"]
            if (
                not isinstance(digest, str)
                or len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest)
                or isinstance(byte_length, bool)
                or not isinstance(byte_length, int)
                or byte_length <= 0
                or not isinstance(entry["kind"], str)
                or not entry["kind"]
                or not isinstance(entry["domain_identity"], str)
                or not entry["domain_identity"]
            ):
                raise SnapshotPublicationError(
                    "snapshot object relation value is invalid"
                )
            object_path = self._object_path(digest)
            if object_path.is_symlink() or not object_path.is_file():
                raise SnapshotPublicationError(
                    "snapshot content-addressed object is unavailable"
                )
            try:
                object_content = object_path.read_bytes()
            except OSError as error:
                raise SnapshotPublicationError(
                    "snapshot content-addressed object is unreadable"
                ) from error
            if (
                len(object_content) != byte_length
                or hashlib.sha256(object_content).hexdigest() != digest
            ):
                raise SnapshotPublicationError(
                    "snapshot content-addressed object is corrupt"
                )
            if entry["kind"] == "source-bytes":
                source_count += 1
            else:
                derived_count += 1
        if (
            source_count != manifest["source_object_count"]
            or derived_count != manifest["derived_object_count"]
        ):
            raise SnapshotPublicationError(
                "snapshot object relation counts are invalid"
            )
        return relation

    def _read_generation(self, manifest: dict[str, object]) -> PublishedCorpusSnapshot:
        base_required = {
            "byte_length",
            "canonical_sha256",
            "generation_name",
            "schema_version",
            "snapshot_id",
        }
        schema_version = manifest.get("schema_version")
        relation_required = {
            "derived_object_count",
            "relation_sha256",
            "source_object_count",
        }
        if (
            schema_version == "bijux.canon.ingest.corpus_publication.v1"
            and set(manifest) != base_required
        ) or (
            schema_version == "bijux.canon.ingest.corpus_publication.v2"
            and set(manifest) != base_required | relation_required
        ):
            raise SnapshotPublicationError("snapshot manifest fields are invalid")
        if schema_version not in {
            "bijux.canon.ingest.corpus_publication.v1",
            "bijux.canon.ingest.corpus_publication.v2",
        }:
            raise SnapshotPublicationError("snapshot manifest schema is unsupported")
        snapshot_id = manifest["snapshot_id"]
        generation_name = manifest["generation_name"]
        canonical_sha256 = manifest["canonical_sha256"]
        byte_length = manifest["byte_length"]
        if (
            not isinstance(snapshot_id, str)
            or not snapshot_id.startswith("sha256:")
            or len(snapshot_id) != 71
            or any(character not in "0123456789abcdef" for character in snapshot_id[7:])
            or not isinstance(generation_name, str)
            or generation_name != snapshot_id.removeprefix("sha256:")
            or not isinstance(canonical_sha256, str)
            or len(canonical_sha256) != 64
            or any(
                character not in "0123456789abcdef" for character in canonical_sha256
            )
            or not isinstance(byte_length, int)
            or isinstance(byte_length, bool)
            or byte_length < 1
        ):
            raise SnapshotPublicationError("snapshot manifest values are invalid")
        relation_sha256 = manifest.get("relation_sha256")
        source_object_count = manifest.get("source_object_count", 0)
        derived_object_count = manifest.get("derived_object_count", 0)
        if (
            isinstance(source_object_count, bool)
            or not isinstance(source_object_count, int)
            or isinstance(derived_object_count, bool)
            or not isinstance(derived_object_count, int)
        ):
            raise SnapshotPublicationError("snapshot relation counts are invalid")
        if schema_version == "bijux.canon.ingest.corpus_publication.v2" and (
            not isinstance(relation_sha256, str)
            or not relation_sha256.startswith("sha256:")
            or len(relation_sha256) != 71
            or any(
                character not in "0123456789abcdef" for character in relation_sha256[7:]
            )
            or source_object_count <= 0
            or derived_object_count <= 0
        ):
            raise SnapshotPublicationError(
                "snapshot relation manifest values are invalid"
            )
        generation = self.generations / generation_name
        snapshot_path = generation / SNAPSHOT_DOCUMENT
        manifest_path = generation / GENERATION_MANIFEST
        if (
            not generation.is_dir()
            or generation.is_symlink()
            or not snapshot_path.is_file()
            or snapshot_path.is_symlink()
            or not manifest_path.is_file()
            or manifest_path.is_symlink()
        ):
            raise SnapshotPublicationError("snapshot generation is incomplete")
        try:
            generation_manifest = manifest_path.read_bytes()
            content = snapshot_path.read_bytes()
        except OSError as error:
            raise SnapshotPublicationError(
                "snapshot generation is incomplete"
            ) from error
        expected_manifest = _canonical_json(manifest)
        if generation_manifest != expected_manifest or len(content) != byte_length:
            raise SnapshotPublicationError(
                "snapshot generation manifest does not match"
            )
        try:
            document = json.loads(content)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise SnapshotPublicationError(
                "snapshot document is not canonical JSON"
            ) from error
        if not isinstance(document, dict) or document.get("snapshot_id") != snapshot_id:
            raise SnapshotPublicationError("snapshot document identity does not match")
        payload = {
            key: value for key, value in document.items() if key != "snapshot_id"
        }
        payload_id = (
            f"sha256:{hashlib.sha256(_canonical_json(payload)[:-1]).hexdigest()}"
        )
        if payload_id != snapshot_id or _canonical_json(document) != content:
            raise SnapshotPublicationError("snapshot document identity is invalid")
        if schema_version == "bijux.canon.ingest.corpus_publication.v2":
            relation = self._read_relation(manifest)
            relation_objects = relation["objects"]
            if not isinstance(relation_objects, list):
                raise SnapshotPublicationError("snapshot object relation is invalid")
            snapshot_entries = [
                entry
                for entry in relation_objects
                if isinstance(entry, dict) and entry.get("kind") == "snapshot"
            ]
            if (
                len(snapshot_entries) != 1
                or snapshot_entries[0].get("object_sha256") != canonical_sha256
                or self._object_path(canonical_sha256).read_bytes() != content
            ):
                raise SnapshotPublicationError(
                    "snapshot object relation does not bind canonical bytes"
                )
        try:
            return PublishedCorpusSnapshot(
                snapshot_id=snapshot_id,
                canonical_bytes=content,
                canonical_sha256=canonical_sha256,
                relation_sha256=(
                    relation_sha256 if isinstance(relation_sha256, str) else None
                ),
                source_object_count=source_object_count,
                derived_object_count=derived_object_count,
            )
        except ValueError as error:
            raise SnapshotPublicationError(str(error)) from error

    def _read_pointer(self, name: str) -> PublishedCorpusSnapshot | None:
        path = self.root / name
        if not path.exists():
            return None
        try:
            content = path.read_bytes()
            manifest = json.loads(content)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise SnapshotPublicationError(
                f"{name} is not a readable snapshot manifest"
            ) from error
        if not isinstance(manifest, dict) or _canonical_json(manifest) != content:
            raise SnapshotPublicationError(f"{name} is not canonical")
        return self._read_generation(manifest)

    def _persist_generation(self, publication: PublishedCorpusSnapshot) -> None:
        destination = self.generations / publication.generation_name
        manifest_bytes = _canonical_json(publication.manifest())
        if destination.exists():
            if self._read_generation(publication.manifest()) != publication:
                raise SnapshotPublicationError("existing generation is inconsistent")
            return
        staged = self.staging / f"generation-{uuid.uuid4().hex}"
        staged.mkdir()
        try:
            _write_new(staged / SNAPSHOT_DOCUMENT, publication.canonical_bytes)
            _write_new(staged / GENERATION_MANIFEST, manifest_bytes)
            _fsync_directory(staged)
            os.replace(staged, destination)
            _fsync_directory(self.generations)
        finally:
            if staged.exists():
                shutil.rmtree(staged)

    def _persist_objects_and_relation(
        self,
        *,
        relation: Mapping[str, object],
        objects: Mapping[str, bytes],
    ) -> None:
        transaction = self.staging / f"publication-{uuid.uuid4().hex}"
        transaction_objects = transaction / "objects"
        transaction.mkdir()
        transaction_objects.mkdir()
        relation_content = _canonical_json(relation)
        try:
            for digest, content in sorted(objects.items()):
                if hashlib.sha256(content).hexdigest() != digest:
                    raise SnapshotPublicationError(
                        "staged content-addressed object identity is invalid"
                    )
                _write_new(transaction_objects / digest, content)
            _fsync_directory(transaction_objects)
            self._checkpoint(PublicationCheckpoint.objects_staged)
            _write_new(transaction / RELATION_DOCUMENT, relation_content)
            _fsync_directory(transaction)
            self._checkpoint(PublicationCheckpoint.relation_staged)

            for staged_object in sorted(transaction_objects.iterdir()):
                digest = staged_object.name
                destination_parent = self.objects / digest[:2]
                self._ensure_directory(destination_parent)
                destination = destination_parent / digest[2:]
                if destination.exists():
                    if (
                        destination.is_symlink()
                        or not destination.is_file()
                        or destination.read_bytes() != staged_object.read_bytes()
                    ):
                        raise SnapshotPublicationError(
                            "existing content-addressed object is inconsistent"
                        )
                    staged_object.unlink()
                else:
                    os.replace(staged_object, destination)
                    _fsync_directory(destination_parent)
            self._checkpoint(PublicationCheckpoint.objects_persisted)

            snapshot_id = relation.get("snapshot_id")
            if not isinstance(snapshot_id, str):
                raise SnapshotPublicationError(
                    "snapshot object relation has no snapshot identity"
                )
            relation_path = self.relations / (
                f"{snapshot_id.removeprefix('sha256:')}.json"
            )
            if relation_path.exists():
                if (
                    relation_path.is_symlink()
                    or not relation_path.is_file()
                    or relation_path.read_bytes() != relation_content
                ):
                    raise SnapshotPublicationError(
                        "existing snapshot object relation is inconsistent"
                    )
                (transaction / RELATION_DOCUMENT).unlink()
            else:
                os.replace(transaction / RELATION_DOCUMENT, relation_path)
                _fsync_directory(self.relations)
            self._checkpoint(PublicationCheckpoint.relation_persisted)
        finally:
            if transaction.exists():
                shutil.rmtree(transaction)

    def publish(self, snapshot: CorpusSnapshot) -> PublishedCorpusSnapshot:
        """Durably persist a generation, then activate its manifest last."""

        self._ensure_layout()
        self._checkpoint(PublicationCheckpoint.layout_ready)
        with self._writer_lock():
            current = self._read_pointer(ACTIVE_MANIFEST)
            if (
                current is not None
                and current.snapshot_id == snapshot.snapshot_id
                and current.canonical_bytes == snapshot.canonical_bytes
            ):
                return current
            relation, objects, source_count, derived_count = self._snapshot_relation(
                snapshot
            )
            relation_sha256 = relation["relation_sha256"]
            if not isinstance(relation_sha256, str):
                raise SnapshotPublicationError(
                    "snapshot object relation identity is invalid"
                )
            publication = self._publication(
                snapshot,
                relation_sha256=relation_sha256,
                source_object_count=source_count,
                derived_object_count=derived_count,
            )
            if current == publication:
                return current
            self._persist_objects_and_relation(relation=relation, objects=objects)
            self._persist_generation(publication)
            self._checkpoint(PublicationCheckpoint.generation_persisted)
            if current is not None:
                self._atomic_write(
                    self.root / PREVIOUS_MANIFEST,
                    _canonical_json(current.manifest()),
                )
            self._checkpoint(PublicationCheckpoint.previous_pointer_persisted)
            self._checkpoint(PublicationCheckpoint.before_activation)
            self._atomic_write(
                self.root / ACTIVE_MANIFEST,
                _canonical_json(publication.manifest()),
            )
            admitted = self._read_pointer(ACTIVE_MANIFEST)
            if admitted != publication:
                raise SnapshotPublicationError("activated snapshot failed verification")
            return publication

    def read_active(self) -> PublishedCorpusSnapshot | None:
        """Read and fully validate the currently admitted generation."""

        self._ensure_layout()
        return self._read_pointer(ACTIVE_MANIFEST)

    def _recover_locked(self) -> SnapshotRecovery:
        self._ensure_layout()
        removed = 0
        for entry in tuple(self.staging.iterdir()):
            if entry.is_dir() and not entry.is_symlink():
                shutil.rmtree(entry)
            else:
                entry.unlink(missing_ok=True)
            removed += 1
        _fsync_directory(self.staging)
        try:
            active = self._read_pointer(ACTIVE_MANIFEST)
        except SnapshotPublicationError:
            active = None
        if active is not None:
            return SnapshotRecovery("healthy", active, removed)
        try:
            previous = self._read_pointer(PREVIOUS_MANIFEST)
        except SnapshotPublicationError as error:
            raise SnapshotPublicationError(
                "no valid admitted snapshot is recoverable"
            ) from error
        if previous is None:
            if (self.root / ACTIVE_MANIFEST).exists():
                raise SnapshotPublicationError(
                    "no valid admitted snapshot is recoverable"
                )
            return SnapshotRecovery("empty", None, removed)
        self._atomic_write(
            self.root / ACTIVE_MANIFEST,
            _canonical_json(previous.manifest()),
        )
        restored = self._read_pointer(ACTIVE_MANIFEST)
        if restored is None:
            raise SnapshotPublicationError(
                "snapshot recovery did not activate a manifest"
            )
        return SnapshotRecovery("recovered", restored, removed)

    def recover(self) -> SnapshotRecovery:
        """Discard interrupted staging and restore the last admitted generation."""

        self._ensure_layout()
        with self._writer_lock():
            return self._recover_locked()


__all__ = [
    "CorpusSnapshotStore",
    "PublicationCheckpoint",
    "PublicationFaultHook",
    "SnapshotPublicationError",
]
