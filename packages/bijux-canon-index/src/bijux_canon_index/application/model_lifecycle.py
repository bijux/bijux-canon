# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Public acquisition, registration, and validation of pinned local models."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
from typing import Any
import uuid

from bijux_canon_index.domain.embedding import (
    LOCAL_MINILM_PROFILE,
    ArtifactDigest,
    EmbeddingModelLock,
    EmbeddingProfile,
)
from bijux_canon_index.infra.embeddings.local_model import LocalEmbeddingModel
from bijux_canon_index.infra.embeddings.model_cache import (
    ModelMaterializationError,
    load_model_lock,
    materialize_model,
    register_model,
    verify_materialized_model,
)

MODEL_RECORD_NAME = "model.record.json"
MODEL_VALIDATION_TEXT = "bijux-canon offline model validation"

_PROFILES = {LOCAL_MINILM_PROFILE.profile_id: LOCAL_MINILM_PROFILE}
_PINNED_ARTIFACTS = (
    ArtifactDigest(
        "1_Pooling/config.json",
        "4be450dde3b0273bb9787637cfbd28fe04a7ba6ab9d36ac48e92b11e350ffc23",
        190,
    ),
    ArtifactDigest(
        "config.json",
        "953f9c0d463486b10a6871cc2fd59f223b2c70184f49815e7efbcab5d8908b41",
        612,
    ),
    ArtifactDigest(
        "config_sentence_transformers.json",
        "061ca9d39661d6c6d6de5ba27f79a1cd5770ea247f8d46412a68a498dc5ac9f3",
        116,
    ),
    ArtifactDigest(
        "model.safetensors",
        "53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db",
        90_868_376,
    ),
    ArtifactDigest(
        "modules.json",
        "84e40c8e006c9b1d6c122e02cba9b02458120b5fb0c87b746c41e0207cf642cf",
        349,
    ),
    ArtifactDigest(
        "sentence_bert_config.json",
        "fc1993fde0a95c24ec6c022539d41cf6e2f7c9721e5415d6fb6897472a9cd4b7",
        53,
    ),
    ArtifactDigest(
        "special_tokens_map.json",
        "303df45a03609e4ead04bc3dc1536d0ab19b5358db685b6f3da123d05ec200e3",
        112,
    ),
    ArtifactDigest(
        "tokenizer.json",
        "be50c3628f2bf5bb5e3a7f17b1f74611b2561a3a27eeab05e5aa30f411572037",
        466_247,
    ),
    ArtifactDigest(
        "tokenizer_config.json",
        "acb92769e8195aabd29b7b2137a9e6d6e25c476a4f15aa4355c233426c61576b",
        350,
    ),
    ArtifactDigest(
        "vocab.txt",
        "07eced375cec144d27c900241f3e339478dec958f92fddbc551f295c992038a3",
        231_508,
    ),
)
_LIBRARY_REQUIREMENTS: tuple[tuple[str, tuple[int, int], int, str], ...] = (
    ("numpy", (1, 26), 3, ">=1.26,<3.0"),
    ("sentence-transformers", (5, 1), 6, ">=5.1,<6.0"),
    ("torch", (2, 7), 3, ">=2.7,<3.0"),
)

ModelLoader = Callable[[Path, str], Any]


class ModelLifecycleError(RuntimeError):
    """A public model lifecycle operation could not validate offline reuse."""


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


def _identity(value: object) -> str:
    return f"sha256:{hashlib.sha256(_canonical_json(value)).hexdigest()}"


def supported_model_profile(profile_id: str) -> EmbeddingProfile:
    """Resolve one supported immutable public model profile."""

    try:
        return _PROFILES[profile_id]
    except KeyError as error:
        supported = ", ".join(sorted(_PROFILES))
        raise ModelLifecycleError(
            f"unsupported embedding profile {profile_id!r}; supported: {supported}"
        ) from error


def installed_library_versions() -> tuple[tuple[str, str], ...]:
    """Capture model-relevant versions used to create a durable lock."""

    names = ("bijux-canon-index", "numpy", "sentence-transformers", "torch")
    try:
        versions = [(name, importlib.metadata.version(name)) for name in names]
    except importlib.metadata.PackageNotFoundError as error:
        missing = error.name or "embedding dependency"
        raise ModelLifecycleError(
            f"required model runtime {missing!r} is unavailable; install the "
            "bijux-canon-index embeddings extra"
        ) from error
    versions.append(("python", platform.python_version()))
    return tuple(sorted(versions))


def model_source(profile: EmbeddingProfile) -> str:
    """Return the immutable upstream source for a pinned profile."""

    return f"https://huggingface.co/{profile.model_id}/tree/{profile.revision}"


def model_license_pointer(profile: EmbeddingProfile) -> str:
    """Return the exact upstream model-card license pointer."""

    return (
        f"https://huggingface.co/{profile.model_id}/blob/{profile.revision}/README.md"
    )


@dataclass(frozen=True, slots=True)
class ModelCompatibility:
    """Observed installed runtime compatibility for one validated model."""

    status: str
    python: str
    python_requirement: str
    libraries: tuple[dict[str, str], ...]

    def record(self) -> dict[str, object]:
        return {
            "libraries": [dict(item) for item in self.libraries],
            "python": self.python,
            "python_requirement": self.python_requirement,
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class ModelValidationRecord:
    """Stable evidence that exact local files can produce locked embeddings."""

    profile_id: str
    source: str
    revision: str
    license_expression: str
    license_pointer: str
    local_files: tuple[dict[str, object], ...]
    artifact_set_digest: str
    model_lock_artifact_id: str
    dimension: int
    compatibility: ModelCompatibility
    validation_result: str = "passed"
    offline_reuse: bool = True
    schema_version: str = "bijux.canon.index.model_validation_record.v1"

    def payload(self) -> dict[str, object]:
        return {
            "artifact_set_digest": self.artifact_set_digest,
            "compatibility": self.compatibility.record(),
            "dimension": self.dimension,
            "license_expression": self.license_expression,
            "license_pointer": self.license_pointer,
            "local_files": [dict(item) for item in self.local_files],
            "model_lock_artifact_id": self.model_lock_artifact_id,
            "offline_reuse": self.offline_reuse,
            "profile_id": self.profile_id,
            "revision": self.revision,
            "schema_version": self.schema_version,
            "source": self.source,
            "validation_result": self.validation_result,
        }

    @property
    def record_id(self) -> str:
        return _identity(self.payload())

    def record(self) -> dict[str, object]:
        return {"record_id": self.record_id, **self.payload()}


def _release_tuple(version: str) -> tuple[int, int]:
    match = re.match(r"^(\d+)\.(\d+)", version)
    if match is None:
        raise ModelLifecycleError(
            f"installed model runtime version {version!r} is not interpretable"
        )
    return int(match.group(1)), int(match.group(2))


def _compatibility() -> ModelCompatibility:
    python = platform.python_version()
    if not (3, 11) <= _release_tuple(python) < (4, 0):
        raise ModelLifecycleError(
            f"Python {python} is incompatible with the required range >=3.11,<4"
        )
    libraries: list[dict[str, str]] = []
    for name, minimum, upper_major, requirement in _LIBRARY_REQUIREMENTS:
        try:
            version = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError as error:
            raise ModelLifecycleError(
                f"required model runtime {name!r} is unavailable; install the "
                "bijux-canon-index embeddings extra"
            ) from error
        release = _release_tuple(version)
        if release < minimum or release[0] >= upper_major:
            raise ModelLifecycleError(
                f"installed {name} {version} is incompatible with {requirement}"
            )
        libraries.append(
            {"installed": version, "name": name, "requirement": requirement}
        )
    return ModelCompatibility(
        status="compatible",
        python=python,
        python_requirement=">=3.11,<4",
        libraries=tuple(libraries),
    )


def _record(lock: EmbeddingModelLock) -> ModelValidationRecord:
    files = tuple(artifact.manifest() for artifact in lock.artifacts)
    return ModelValidationRecord(
        profile_id=lock.profile.profile_id,
        source=model_source(lock.profile),
        revision=lock.profile.revision,
        license_expression=lock.profile.license_expression,
        license_pointer=model_license_pointer(lock.profile),
        local_files=files,
        artifact_set_digest=_identity([dict(item) for item in files]),
        model_lock_artifact_id=lock.lock_id,
        dimension=lock.profile.dimension,
        compatibility=_compatibility(),
    )


def _write_record(root: Path, record: ModelValidationRecord) -> None:
    destination = root / MODEL_RECORD_NAME
    temporary = root / f".{MODEL_RECORD_NAME}.{uuid.uuid4().hex}"
    try:
        with temporary.open("xb") as stream:
            stream.write(_canonical_json(record.record()))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def validate_model(
    model_root: str | Path,
    *,
    profile_id: str = LOCAL_MINILM_PROFILE.profile_id,
    loader: ModelLoader | None = None,
) -> ModelValidationRecord:
    """Verify exact files and execute one bounded CPU embedding smoke offline."""

    root = Path(model_root)
    profile = supported_model_profile(profile_id)
    try:
        lock = load_model_lock(root / "model.lock.json")
        if lock.profile != profile:
            raise ModelLifecycleError(
                "model lock does not match the selected pinned profile"
            )
        verify_materialized_model(root, lock)
        if lock.artifacts != _PINNED_ARTIFACTS:
            raise ModelLifecycleError(
                "model files do not match the selected pinned revision"
            )
        adapter = (
            LocalEmbeddingModel(root, lock, batch_size=1, device="cpu")
            if loader is None
            else LocalEmbeddingModel(
                root,
                lock,
                batch_size=1,
                device="cpu",
                loader=loader,
            )
        )
        embedded = adapter.embed((MODEL_VALIDATION_TEXT,))
        if embedded.model_lock_id != lock.lock_id:
            raise ModelLifecycleError(
                "embedding smoke returned the wrong model identity"
            )
        record = _record(lock)
        _write_record(root, record)
        return record
    except ModelLifecycleError:
        raise
    except (ImportError, ModelMaterializationError, OSError, ValueError) as error:
        raise ModelLifecycleError(f"model validation failed: {error}") from error


def acquire_model(
    cache_root: str | Path,
    *,
    profile_id: str = LOCAL_MINILM_PROFILE.profile_id,
) -> ModelValidationRecord:
    """Acquire a pinned revision, or reuse its validated cache without network."""

    profile = supported_model_profile(profile_id)
    root = Path(cache_root) / profile.profile_id / profile.revision
    try:
        if not root.exists():
            materialize_model(
                profile,
                cache_root,
                library_versions=installed_library_versions(),
            )
    except (ModelMaterializationError, OSError, ValueError) as error:
        raise ModelLifecycleError(f"model acquisition failed: {error}") from error
    return validate_model(root, profile_id=profile_id)


def register_existing_model(
    model_root: str | Path,
    *,
    profile_id: str = LOCAL_MINILM_PROFILE.profile_id,
) -> ModelValidationRecord:
    """Register already downloaded pinned files and validate offline inference."""

    profile = supported_model_profile(profile_id)
    try:
        register_model(
            profile,
            model_root,
            library_versions=installed_library_versions(),
            expected_artifacts=_PINNED_ARTIFACTS,
        )
    except (ModelMaterializationError, OSError, ValueError) as error:
        raise ModelLifecycleError(f"model registration failed: {error}") from error
    return validate_model(model_root, profile_id=profile_id)


def load_model_record(path: str | Path) -> ModelValidationRecord:
    """Load and authenticate one canonical durable validation record."""

    try:
        content = Path(path).read_bytes()
        manifest = json.loads(content)
        if not isinstance(manifest, dict) or _canonical_json(manifest) != content:
            raise ValueError
        record_id = manifest.pop("record_id")
        compatibility_value = manifest.pop("compatibility")
        local_files = manifest.pop("local_files")
        if not isinstance(compatibility_value, dict) or not isinstance(
            local_files, list
        ):
            raise ValueError
        libraries = compatibility_value.get("libraries")
        if not isinstance(libraries, list):
            raise ValueError
        compatibility = ModelCompatibility(
            status=str(compatibility_value["status"]),
            python=str(compatibility_value["python"]),
            python_requirement=str(compatibility_value["python_requirement"]),
            libraries=tuple(dict(item) for item in libraries),
        )
        record = ModelValidationRecord(
            compatibility=compatibility,
            local_files=tuple(dict(item) for item in local_files),
            **manifest,
        )
        if record_id != record.record_id:
            raise ValueError
        return record
    except (KeyError, OSError, TypeError, UnicodeDecodeError, ValueError) as error:
        raise ModelLifecycleError("model validation record is invalid") from error


__all__ = [
    "acquire_model",
    "installed_library_versions",
    "load_model_record",
    "MODEL_RECORD_NAME",
    "ModelCompatibility",
    "ModelLifecycleError",
    "ModelValidationRecord",
    "register_existing_model",
    "supported_model_profile",
    "validate_model",
]
