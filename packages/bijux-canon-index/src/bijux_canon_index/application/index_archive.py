# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Portable canonical archives for complete immutable index generations."""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import tempfile

from bijux_canon_index.application.index_activation import IndexGenerationRegistry
from bijux_canon_index.application.index_generation import (
    EXACT_NAME,
    HNSW_NAME,
    LEXICAL_NAME,
    MANIFEST_NAME,
    IndexGeneration,
)
from bijux_canon_index.application.index_inspection import IndexInspectionReport
from bijux_canon_index.application.index_resource_cache import (
    IndexGenerationResourceCache,
)

ARCHIVE_SCHEMA_VERSION = "bijux.canon.index.generation_archive.v1"
_FILE_NAMES = (LEXICAL_NAME, EXACT_NAME, HNSW_NAME, MANIFEST_NAME)


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


@dataclass(frozen=True, slots=True)
class IndexGenerationArchiveFile:
    """One named generation file with verified immutable content."""

    name: str
    content: bytes
    sha256: str

    def __post_init__(self) -> None:
        if self.name not in _FILE_NAMES:
            raise ValueError("index archive file name is unsupported")
        if hashlib.sha256(self.content).hexdigest() != self.sha256:
            raise ValueError("index archive file hash does not match its content")

    def manifest(self) -> dict[str, object]:
        return {
            "byte_length": len(self.content),
            "content_base64": base64.b64encode(self.content).decode("ascii"),
            "name": self.name,
            "sha256": self.sha256,
        }


@dataclass(frozen=True, slots=True)
class IndexGenerationArchive:
    """Canonical payload containing every file in one verified generation."""

    generation_id: str
    files: tuple[IndexGenerationArchiveFile, ...]

    def __post_init__(self) -> None:
        if tuple(item.name for item in self.files) != _FILE_NAMES:
            raise ValueError(
                "index archive must contain every generation file in order"
            )
        if not self.generation_id.startswith("sha256:"):
            raise ValueError("index archive generation identity is invalid")

    @property
    def canonical_bytes(self) -> bytes:
        """Return deterministic bytes suitable for a content-addressed store."""

        return _canonical_json(
            {
                "files": [item.manifest() for item in self.files],
                "generation_id": self.generation_id,
                "schema_version": ARCHIVE_SCHEMA_VERSION,
            }
        )

    @classmethod
    def from_generation(cls, path: str | Path) -> IndexGenerationArchive:
        """Export one verified generation without relying on its filesystem path."""

        with IndexGeneration.open(path) as generation:
            files = []
            for name in _FILE_NAMES:
                content = (generation.path / name).read_bytes()
                files.append(
                    IndexGenerationArchiveFile(
                        name,
                        content,
                        hashlib.sha256(content).hexdigest(),
                    )
                )
            return cls(generation.manifest.generation_id, tuple(files))

    @classmethod
    def from_bytes(cls, content: bytes) -> IndexGenerationArchive:
        """Parse and verify one canonical archive payload."""

        try:
            payload = json.loads(content)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("index generation archive is unreadable") from error
        if not isinstance(payload, dict) or set(payload) != {
            "files",
            "generation_id",
            "schema_version",
        }:
            raise ValueError("index generation archive fields are unsupported")
        if payload["schema_version"] != ARCHIVE_SCHEMA_VERSION:
            raise ValueError("index generation archive schema is unsupported")
        if content != _canonical_json(payload):
            raise ValueError("index generation archive is not canonical JSON")
        raw_files = payload["files"]
        if not isinstance(raw_files, list):
            raise ValueError("index generation archive files are invalid")
        files: list[IndexGenerationArchiveFile] = []
        try:
            for raw in raw_files:
                if not isinstance(raw, dict) or set(raw) != {
                    "byte_length",
                    "content_base64",
                    "name",
                    "sha256",
                }:
                    raise ValueError("index archive file fields are unsupported")
                encoded = raw["content_base64"]
                if not isinstance(encoded, str):
                    raise TypeError
                decoded = base64.b64decode(encoded, validate=True)
                if len(decoded) != raw["byte_length"]:
                    raise ValueError("index archive file length does not match")
                files.append(
                    IndexGenerationArchiveFile(
                        name=str(raw["name"]),
                        content=decoded,
                        sha256=str(raw["sha256"]),
                    )
                )
        except (TypeError, ValueError, binascii.Error) as error:
            raise ValueError("index generation archive file is invalid") from error
        return cls(str(payload["generation_id"]), tuple(files))

    def materialize(self, path: str | Path) -> IndexGeneration:
        """Publish and verify the archived files at a new destination."""

        destination = Path(path).resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise FileExistsError(destination)
        destination.mkdir()
        try:
            for archived in self.files:
                target = destination / archived.name
                with target.open("xb") as handle:
                    handle.write(archived.content)
                    handle.flush()
                    os.fsync(handle.fileno())
            descriptor = os.open(destination, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            generation = IndexGeneration.open(destination)
            if generation.manifest.generation_id != self.generation_id:
                generation.close()
                raise ValueError("index archive generation identity does not match")
            return generation
        except BaseException:
            for name in reversed(_FILE_NAMES):
                (destination / name).unlink(missing_ok=True)
            destination.rmdir()
            raise


def export_index_generation(
    registry_root: str | Path,
    generation_id: str,
) -> IndexGenerationArchive:
    """Export one admitted generation through the registry authority."""

    registry = IndexGenerationRegistry(registry_root)
    with registry.open(generation_id) as generation:
        return IndexGenerationArchive.from_generation(generation.path)


def admit_index_generation_archive(
    registry_root: str | Path,
    content: bytes,
    *,
    activate: bool = False,
    resource_cache: IndexGenerationResourceCache | None = None,
) -> IndexInspectionReport:
    """Verify, admit, and optionally activate one portable generation archive."""

    registry = IndexGenerationRegistry(
        registry_root,
        resource_cache=resource_cache,
    )
    archive = IndexGenerationArchive.from_bytes(content)
    with (
        tempfile.TemporaryDirectory(
            prefix=".archive-admission-",
            dir=registry.root,
        ) as work,
        archive.materialize(Path(work) / "generation") as generation,
    ):
        generation_id = registry.admit(generation.path)
    if activate:
        registry.activate(generation_id)
    return registry.inspect(generation_id)


__all__ = [
    "ARCHIVE_SCHEMA_VERSION",
    "IndexGenerationArchive",
    "IndexGenerationArchiveFile",
    "admit_index_generation_archive",
    "export_index_generation",
]
