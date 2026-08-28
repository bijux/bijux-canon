# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Verified acquisition and offline loading of locked embedding models."""

from __future__ import annotations

from collections.abc import Callable
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import sys
import urllib.parse
import urllib.request
import uuid

from bijux_canon_index.domain.embedding import (
    ArtifactDigest,
    EmbeddingModelLock,
    EmbeddingProfile,
)

MetadataFetcher = Callable[[str], dict[str, object]]
ArtifactFetcher = Callable[[str, Path], None]


class ModelMaterializationError(RuntimeError):
    """Pinned model metadata or artifacts failed verification."""

    def __init__(
        self,
        message: str,
        *,
        remediation_command: tuple[str, ...] | None = None,
    ) -> None:
        self.remediation_command = remediation_command
        if remediation_command is not None:
            message = f"{message}; materialize with: {shlex.join(remediation_command)}"
        super().__init__(message)


def materialization_command(
    model_root: str | Path,
    profile: EmbeddingProfile,
) -> tuple[str, ...]:
    """Return the exact installed-module command for a missing model cache."""

    root = Path(model_root)
    cache_root = (
        root.parent.parent
        if root.name == profile.revision and root.parent.name == profile.profile_id
        else root
    )
    return (
        sys.executable,
        "-m",
        "bijux_canon_index.tooling.embedding_models",
        "--profile",
        profile.profile_id,
        "--cache-root",
        str(cache_root),
    )


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


def _fetch_metadata(url: str) -> dict[str, object]:
    with urllib.request.urlopen(url, timeout=30) as response:
        value = json.load(response)
    if not isinstance(value, dict):
        raise ModelMaterializationError("model repository metadata is not an object")
    return value


def _fetch_artifact(url: str, destination: Path) -> None:
    with (
        urllib.request.urlopen(url, timeout=120) as response,
        destination.open("xb") as output,
    ):
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
        output.flush()
        os.fsync(output.fileno())


def _fsync_directory(path: Path) -> None:
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    except OSError:
        if os.name == "nt":
            return
        raise
    try:
        os.fsync(descriptor)
    except OSError:
        if os.name != "nt":
            raise
    finally:
        os.close(descriptor)


def _write_lock(path: Path, content: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def _digest(path: Path, relative_path: str) -> ArtifactDigest:
    digest = hashlib.sha256()
    byte_length = 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
            byte_length += len(chunk)
    return ArtifactDigest(relative_path, digest.hexdigest(), byte_length)


def _repository_urls(profile: EmbeddingProfile) -> tuple[str, str]:
    encoded_model = "/".join(
        urllib.parse.quote(part, safe="") for part in profile.model_id.split("/")
    )
    base = f"https://huggingface.co/{encoded_model}"
    metadata = (
        f"https://huggingface.co/api/models/{encoded_model}/revision/{profile.revision}"
    )
    return base, metadata


def _validate_repository_metadata(
    profile: EmbeddingProfile,
    metadata: dict[str, object],
) -> None:
    if metadata.get("sha") != profile.revision:
        raise ModelMaterializationError("model repository revision does not match")
    card = metadata.get("cardData")
    if not isinstance(card, dict) or card.get("license") != "apache-2.0":
        raise ModelMaterializationError("model repository license is not Apache-2.0")
    siblings = metadata.get("siblings")
    if not isinstance(siblings, list):
        raise ModelMaterializationError("model repository file inventory is missing")
    available = {item.get("rfilename") for item in siblings if isinstance(item, dict)}
    missing = set(profile.required_artifacts) - available
    if missing:
        raise ModelMaterializationError(
            f"model repository is missing required artifacts: {sorted(missing)}"
        )


def verify_materialized_model(
    root: str | Path,
    lock: EmbeddingModelLock,
) -> None:
    """Verify an offline cache without attempting any network access."""

    model_root = Path(root)
    for expected in lock.artifacts:
        path = model_root / expected.path
        if not path.is_file() or path.is_symlink():
            raise ModelMaterializationError(
                f"offline model artifact is missing: {expected.path}",
                remediation_command=materialization_command(model_root, lock.profile),
            )
        if _digest(path, expected.path) != expected:
            raise ModelMaterializationError(
                f"offline model artifact is corrupt: {expected.path}"
            )


def load_model_lock(path: str | Path) -> EmbeddingModelLock:
    """Load a canonical saved lock for network-free cache verification."""

    try:
        content = Path(path).read_bytes()
        manifest = json.loads(content)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ModelMaterializationError("embedding model lock is unreadable") from error
    if not isinstance(manifest, dict) or _canonical_json(manifest) != content:
        raise ModelMaterializationError("embedding model lock is not canonical")
    try:
        profile_value = manifest["profile"]
        artifacts_value = manifest["artifacts"]
        versions_value = manifest["library_versions"]
        if (
            not isinstance(profile_value, dict)
            or not isinstance(artifacts_value, list)
            or not isinstance(versions_value, dict)
        ):
            raise TypeError
        profile_fields = dict(profile_value)
        profile_fields.pop("schema_version")
        required = profile_fields["required_artifacts"]
        if not isinstance(required, list):
            raise TypeError
        profile_fields["required_artifacts"] = tuple(required)
        profile = EmbeddingProfile(**profile_fields)
        artifacts = tuple(ArtifactDigest(**value) for value in artifacts_value)
        versions = tuple(
            sorted((str(key), str(value)) for key, value in versions_value.items())
        )
        lock = EmbeddingModelLock(profile, artifacts, versions)
    except (KeyError, TypeError, ValueError) as error:
        raise ModelMaterializationError(
            "embedding model lock fields are invalid"
        ) from error
    if manifest != lock.manifest():
        raise ModelMaterializationError("embedding model lock identity is invalid")
    return lock


def materialize_model(
    profile: EmbeddingProfile,
    cache_root: str | Path,
    *,
    library_versions: tuple[tuple[str, str], ...],
    metadata_fetcher: MetadataFetcher = _fetch_metadata,
    artifact_fetcher: ArtifactFetcher = _fetch_artifact,
) -> EmbeddingModelLock:
    """Acquire a pinned model into a revision-addressed offline cache."""

    if profile.provider_kind != "local" or profile.offline_policy != "required":
        raise ModelMaterializationError(
            "only offline-required local profiles can be materialized"
        )
    base_url, metadata_url = _repository_urls(profile)
    metadata = metadata_fetcher(metadata_url)
    _validate_repository_metadata(profile, metadata)
    destination = Path(cache_root) / profile.profile_id / profile.revision
    if destination.exists():
        raise ModelMaterializationError(
            "model cache revision already exists; verify it with its saved lock"
        )
    staging_root = Path(cache_root) / "staging"
    staging_root.mkdir(parents=True, exist_ok=True)
    staged = staging_root / f"model-{uuid.uuid4().hex}"
    staged.mkdir()
    try:
        artifacts: list[ArtifactDigest] = []
        for relative_path in profile.required_artifacts:
            target = staged / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            encoded_path = "/".join(
                urllib.parse.quote(part, safe="") for part in relative_path.split("/")
            )
            artifact_fetcher(
                f"{base_url}/resolve/{profile.revision}/{encoded_path}",
                target,
            )
            artifacts.append(_digest(target, relative_path))
        lock = EmbeddingModelLock(
            profile,
            tuple(artifacts),
            library_versions,
        )
        _write_lock(staged / "model.lock.json", _canonical_json(lock.manifest()))
        _fsync_directory(staged)
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.replace(staged, destination)
        _fsync_directory(destination.parent)
        verify_materialized_model(destination, lock)
        return lock
    except Exception:
        if staged.exists():
            shutil.rmtree(staged)
        raise


def register_model(
    profile: EmbeddingProfile,
    model_root: str | Path,
    *,
    library_versions: tuple[tuple[str, str], ...],
    expected_artifacts: tuple[ArtifactDigest, ...] | None = None,
) -> EmbeddingModelLock:
    """Bind an existing pinned model directory to a canonical offline lock."""

    root = Path(model_root)
    if not root.is_dir() or root.is_symlink():
        raise ModelMaterializationError(
            "model registration requires an existing ordinary directory"
        )
    lock_path = root / "model.lock.json"
    if lock_path.exists():
        lock = load_model_lock(lock_path)
        if lock.profile != profile:
            raise ModelMaterializationError(
                "existing model lock does not match the selected pinned profile"
            )
        verify_materialized_model(root, lock)
        return lock
    artifacts: list[ArtifactDigest] = []
    for relative_path in profile.required_artifacts:
        path = root / relative_path
        if not path.is_file() or path.is_symlink():
            raise ModelMaterializationError(
                f"model registration is missing required artifact: {relative_path}"
            )
        artifacts.append(_digest(path, relative_path))
    if expected_artifacts is not None and tuple(artifacts) != expected_artifacts:
        raise ModelMaterializationError(
            "model files do not match the selected pinned revision"
        )
    lock = EmbeddingModelLock(profile, tuple(artifacts), library_versions)
    temporary_lock = root / f".model.lock.{uuid.uuid4().hex}.json"
    try:
        _write_lock(temporary_lock, _canonical_json(lock.manifest()))
        os.replace(temporary_lock, lock_path)
        _fsync_directory(root)
    finally:
        temporary_lock.unlink(missing_ok=True)
    verify_materialized_model(root, lock)
    return lock


__all__ = [
    "load_model_lock",
    "materialization_command",
    "ModelMaterializationError",
    "materialize_model",
    "register_model",
    "verify_materialized_model",
]
