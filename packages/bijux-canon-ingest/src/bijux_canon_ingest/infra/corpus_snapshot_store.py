# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Crash-safe filesystem publication for canonical corpus snapshots."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
from typing import Final
import uuid

from bijux_canon_ingest.domain.corpus_publication import (
    PublishedCorpusSnapshot,
    SnapshotRecovery,
)
from bijux_canon_ingest.domain.corpus_snapshot import CorpusSnapshot

ACTIVE_MANIFEST: Final = "active.json"
PREVIOUS_MANIFEST: Final = "previous.json"
GENERATION_MANIFEST: Final = "manifest.json"
SNAPSHOT_DOCUMENT: Final = "snapshot.json"


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

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.generations = self.root / "generations"
        self.staging = self.root / "staging"

    def _ensure_layout(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.generations.mkdir(exist_ok=True)
        self.staging.mkdir(exist_ok=True)
        _fsync_directory(self.root)

    def _atomic_write(self, destination: Path, content: bytes) -> None:
        staged = self.staging / f"activation-{uuid.uuid4().hex}.json"
        try:
            _write_new(staged, content)
            os.replace(staged, destination)
            _fsync_directory(destination.parent)
        finally:
            staged.unlink(missing_ok=True)

    def _publication(self, snapshot: CorpusSnapshot) -> PublishedCorpusSnapshot:
        content = snapshot.canonical_bytes
        return PublishedCorpusSnapshot(
            snapshot_id=snapshot.snapshot_id,
            canonical_bytes=content,
            canonical_sha256=hashlib.sha256(content).hexdigest(),
        )

    def _read_generation(self, manifest: dict[str, object]) -> PublishedCorpusSnapshot:
        required = {
            "byte_length",
            "canonical_sha256",
            "generation_name",
            "schema_version",
            "snapshot_id",
        }
        if set(manifest) != required:
            raise SnapshotPublicationError("snapshot manifest fields are invalid")
        if manifest["schema_version"] != "bijux.canon.ingest.corpus_publication.v1":
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
        try:
            return PublishedCorpusSnapshot(
                snapshot_id=snapshot_id,
                canonical_bytes=content,
                canonical_sha256=canonical_sha256,
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

    def publish(self, snapshot: CorpusSnapshot) -> PublishedCorpusSnapshot:
        """Durably persist a generation, then activate its manifest last."""

        self._ensure_layout()
        current = self._read_pointer(ACTIVE_MANIFEST)
        publication = self._publication(snapshot)
        if current == publication:
            return current
        self._persist_generation(publication)
        if current is not None:
            self._atomic_write(
                self.root / PREVIOUS_MANIFEST,
                _canonical_json(current.manifest()),
            )
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

    def recover(self) -> SnapshotRecovery:
        """Discard interrupted staging and restore the last admitted generation."""

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


__all__ = ["CorpusSnapshotStore", "SnapshotPublicationError"]
