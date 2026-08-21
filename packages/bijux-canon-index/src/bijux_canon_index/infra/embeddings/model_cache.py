# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Verified acquisition and offline loading of locked embedding models."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import urllib.parse
import urllib.request
import uuid
from collections.abc import Callable
from pathlib import Path

from bijux_canon_index.domain.embedding import (
    ArtifactDigest,
    EmbeddingModelLock,
    EmbeddingProfile,
)

MetadataFetcher = Callable[[str], dict[str, object]]
ArtifactFetcher = Callable[[str, Path], None]


class ModelMaterializationError(RuntimeError):
    """Pinned model metadata or artifacts failed verification."""


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
    with urllib.request.urlopen(url, timeout=120) as response:
        with destination.open("xb") as output:
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
                f"offline model artifact is missing: {expected.path}"
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


__all__ = [
    "load_model_lock",
    "ModelMaterializationError",
    "materialize_model",
    "verify_materialized_model",
]
