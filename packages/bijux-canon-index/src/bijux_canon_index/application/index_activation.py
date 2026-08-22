# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Admit and atomically activate immutable index generations."""

from __future__ import annotations

from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Iterator

from bijux_canon_index.application.index_audit import (
    IndexCompatibility,
    audit_index_generation,
)
from bijux_canon_index.application.index_generation import (
    EXACT_NAME,
    HNSW_NAME,
    LEXICAL_NAME,
    MANIFEST_NAME,
    IndexGeneration,
)
from bijux_canon_index.application.index_inspection import (
    IndexInspectionReport,
    inspect_index_generation,
)

ACTIVE_NAME = "active.json"
GENERATIONS_NAME = "generations"
LOCK_NAME = "registry.lock"
_SEGMENT_NAMES = (LEXICAL_NAME, EXACT_NAME, HNSW_NAME)


class IndexActivationError(RuntimeError):
    """An admitted generation cannot be resolved or activated safely."""


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _generation_directory_name(generation_id: str) -> str:
    prefix = "sha256:"
    if not generation_id.startswith(prefix):
        raise IndexActivationError("generation identity is not content-addressed")
    digest = generation_id.removeprefix(prefix)
    if len(digest) != 64 or any(value not in "0123456789abcdef" for value in digest):
        raise IndexActivationError("generation identity digest is invalid")
    return digest


class IndexGenerationRegistry:
    """Persistent manifest-last registry with one atomic active pointer."""

    def __init__(
        self,
        root: str | Path,
        *,
        compatibility: IndexCompatibility | None = None,
    ) -> None:
        self.root = Path(root).resolve()
        self.generations = self.root / GENERATIONS_NAME
        self.root.mkdir(parents=True, exist_ok=True)
        self.generations.mkdir(exist_ok=True)
        (self.root / LOCK_NAME).touch(exist_ok=True)
        self._compatibility = compatibility

    @contextmanager
    def _exclusive(self) -> Iterator[None]:
        with (self.root / LOCK_NAME).open("rb") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def admit(self, source: str | Path) -> str:
        """Verify and publish a complete generation without activating it."""

        source_path = Path(source).resolve()
        audit = audit_index_generation(source_path, compatibility=self._compatibility)
        generation_id = audit.generation_id
        destination = self.generations / _generation_directory_name(generation_id)
        with self._exclusive():
            if destination.exists():
                with IndexGeneration.open(destination) as existing:
                    if existing.manifest.generation_id != generation_id:
                        raise IndexActivationError(
                            "admitted generation identity collided"
                        )
                return generation_id
            temporary = Path(
                tempfile.mkdtemp(
                    prefix=f".{destination.name}.",
                    suffix=".building",
                    dir=self.generations,
                )
            )
            try:
                for name in _SEGMENT_NAMES:
                    source_file = source_path / name
                    if not source_file.is_file():
                        raise IndexActivationError(
                            f"generation segment is missing: {name}"
                        )
                    shutil.copyfile(source_file, temporary / name)
                    with (temporary / name).open("rb") as handle:
                        os.fsync(handle.fileno())
                manifest_source = source_path / MANIFEST_NAME
                shutil.copyfile(manifest_source, temporary / MANIFEST_NAME)
                with (temporary / MANIFEST_NAME).open("rb") as handle:
                    os.fsync(handle.fileno())
                with IndexGeneration.open(temporary) as copied:
                    if copied.manifest.generation_id != generation_id:
                        raise IndexActivationError("copied generation identity changed")
                descriptor = os.open(temporary, os.O_RDONLY)
                try:
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
                os.rename(temporary, destination)
                self._fsync_directory(self.generations)
            except BaseException:
                shutil.rmtree(temporary, ignore_errors=True)
                raise
        return generation_id

    def activate(self, generation_id: str) -> None:
        """Atomically replace the active pointer after complete verification."""

        generation_path = self.generations / _generation_directory_name(generation_id)
        with self._exclusive():
            audit = audit_index_generation(
                generation_path, compatibility=self._compatibility
            )
            if audit.generation_id != generation_id:
                raise IndexActivationError("generation path and identity diverged")
            previous = self.active_generation_id(required=False)
            payload = {
                "generation_id": generation_id,
                "generation_manifest_sha256": _sha256_file(
                    generation_path / MANIFEST_NAME
                ),
                "previous_generation_id": previous,
                "schema_version": "bijux.canon.index.active_generation.v1",
            }
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=".active.", suffix=".building", dir=self.root
            )
            temporary = Path(temporary_name)
            try:
                with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                    handle.write(_canonical_json(payload) + "\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, self.root / ACTIVE_NAME)
                self._fsync_directory(self.root)
            except BaseException:
                temporary.unlink(missing_ok=True)
                raise

    def active_generation_id(self, *, required: bool = True) -> str | None:
        """Return the verified active identity from one pointer read."""

        pointer = self.root / ACTIVE_NAME
        if not pointer.is_file():
            if required:
                raise IndexActivationError("no index generation is active")
            return None
        raw = pointer.read_bytes()
        try:
            payload = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise IndexActivationError(
                "active generation pointer is unreadable"
            ) from error
        expected = {
            "generation_id",
            "generation_manifest_sha256",
            "previous_generation_id",
            "schema_version",
        }
        if not isinstance(payload, dict) or set(payload) != expected:
            raise IndexActivationError(
                "active generation pointer fields are unsupported"
            )
        if raw != (_canonical_json(payload) + "\n").encode("utf-8"):
            raise IndexActivationError("active generation pointer is not canonical")
        generation_id = str(payload["generation_id"])
        generation_path = self.generations / _generation_directory_name(generation_id)
        if (
            _sha256_file(generation_path / MANIFEST_NAME)
            != payload["generation_manifest_sha256"]
        ):
            raise IndexActivationError("active generation manifest hash mismatches")
        return generation_id

    def open_active(self) -> IndexGeneration:
        """Open the generation named by one verified pointer snapshot."""

        return self.open()

    def open(self, generation_id: str | None = None) -> IndexGeneration:
        """Open one admitted generation, defaulting to the active pointer."""

        selected_generation_id = generation_id or self.active_generation_id()
        assert selected_generation_id is not None
        path = self.generations / _generation_directory_name(selected_generation_id)
        audit_index_generation(path, compatibility=self._compatibility)
        return IndexGeneration.open(path)

    def inspect(self, generation_id: str | None = None) -> IndexInspectionReport:
        """Return a verified content-safe report for an admitted generation."""

        active_generation_id = self.active_generation_id(required=False)
        selected_generation_id = generation_id or active_generation_id
        if selected_generation_id is None:
            raise IndexActivationError("no index generation is available to inspect")
        path = self.generations / _generation_directory_name(selected_generation_id)
        return inspect_index_generation(
            path,
            compatibility=self._compatibility,
            active_generation_id=active_generation_id,
        )

    def recover(self) -> tuple[str, ...]:
        """Remove only recognized interrupted publications and verify activation."""

        removed = []
        with self._exclusive():
            for path in sorted(self.generations.glob(".*.building")):
                if path.is_dir():
                    shutil.rmtree(path)
                    removed.append(path.name)
            for path in sorted(self.root.glob(".active.*.building")):
                if path.is_file():
                    path.unlink()
                    removed.append(path.name)
            if removed:
                self._fsync_directory(self.generations)
                self._fsync_directory(self.root)
            self.active_generation_id(required=False)
        return tuple(removed)

    @staticmethod
    def _fsync_directory(path: Path) -> None:
        descriptor = os.open(path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


__all__ = ["IndexActivationError", "IndexGenerationRegistry"]
