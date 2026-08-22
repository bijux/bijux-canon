# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Immutable embedding profiles and materialized model locks."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import PurePosixPath
from typing import Literal

ProviderKind = Literal["local", "remote", "qualification"]
OfflinePolicy = Literal["required", "allowed", "forbidden"]
SupportTier = Literal["production", "optional", "qualification"]
CompatibilityOperation = Literal["build", "query", "execution"]


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256_identity(value: object) -> str:
    return f"sha256:{hashlib.sha256(_canonical_json(value)).hexdigest()}"


def _portable_path(value: str) -> bool:
    path = PurePosixPath(value)
    return (
        bool(value)
        and not value.startswith("/")
        and "\\" not in value
        and all(part not in {"", ".", ".."} for part in path.parts)
    )


@dataclass(frozen=True, slots=True)
class ArtifactDigest:
    """One content-addressed file required by a materialized model."""

    path: str
    sha256: str
    byte_length: int

    def __post_init__(self) -> None:
        if not _portable_path(self.path):
            raise ValueError("embedding artifact path must be portable and relative")
        if len(self.sha256) != 64 or any(
            character not in "0123456789abcdef" for character in self.sha256
        ):
            raise ValueError("embedding artifact requires a lowercase SHA-256")
        if self.byte_length < 1:
            raise ValueError("embedding artifact must not be empty")

    def manifest(self) -> dict[str, object]:
        return {
            "byte_length": self.byte_length,
            "path": self.path,
            "sha256": self.sha256,
        }


@dataclass(frozen=True, slots=True)
class EmbeddingProfile:
    """Declared semantic and operational identity before artifact acquisition."""

    profile_id: str
    provider_kind: ProviderKind
    provider: str
    model_id: str
    revision: str
    dimension: int
    dtype: str
    normalization: str
    pooling: str
    tokenizer_id: str
    tokenizer_revision: str
    license_expression: str
    device_policy: str
    numeric_policy: str
    offline_policy: OfflinePolicy
    support_tier: SupportTier
    required_artifacts: tuple[str, ...]

    def __post_init__(self) -> None:
        identifiers = (
            self.profile_id,
            self.provider,
            self.model_id,
            self.revision,
            self.tokenizer_id,
            self.tokenizer_revision,
            self.license_expression,
            self.device_policy,
            self.numeric_policy,
        )
        if any(not value for value in identifiers) or self.dimension < 1:
            raise ValueError("embedding profile identity fields must be complete")
        if self.dtype not in {"float32", "float64"}:
            raise ValueError("embedding profile dtype is unsupported")
        if self.normalization not in {"l2", "none"}:
            raise ValueError("embedding profile normalization is unsupported")
        if self.pooling not in {"mean", "cls", "provider"}:
            raise ValueError("embedding profile pooling is unsupported")
        if self.provider_kind == "local" and (
            len(self.revision) != 40
            or any(character not in "0123456789abcdef" for character in self.revision)
        ):
            raise ValueError("local embedding revision must be an immutable Git SHA")
        if self.offline_policy not in {"required", "allowed", "forbidden"}:
            raise ValueError("embedding profile offline policy is unsupported")
        if self.support_tier not in {"production", "optional", "qualification"}:
            raise ValueError("embedding profile support tier is unsupported")
        if self.support_tier == "production" and self.provider_kind == "qualification":
            raise ValueError("qualification providers cannot be production profiles")
        if self.required_artifacts != tuple(
            sorted(set(self.required_artifacts))
        ) or any(not _portable_path(path) for path in self.required_artifacts):
            raise ValueError("required embedding artifacts must be unique and ordered")

    def manifest(self) -> dict[str, object]:
        return {
            "device_policy": self.device_policy,
            "dimension": self.dimension,
            "dtype": self.dtype,
            "license_expression": self.license_expression,
            "model_id": self.model_id,
            "normalization": self.normalization,
            "numeric_policy": self.numeric_policy,
            "offline_policy": self.offline_policy,
            "pooling": self.pooling,
            "profile_id": self.profile_id,
            "provider": self.provider,
            "provider_kind": self.provider_kind,
            "required_artifacts": list(self.required_artifacts),
            "revision": self.revision,
            "schema_version": "bijux.canon.index.embedding_profile.v1",
            "support_tier": self.support_tier,
            "tokenizer_id": self.tokenizer_id,
            "tokenizer_revision": self.tokenizer_revision,
        }


class EmbeddingModelMismatchError(ValueError):
    """Typed model-lock incompatibility with a durable recovery action."""

    def __init__(
        self,
        *,
        expected_lock_id: str,
        actual_lock_id: str,
        mismatches: tuple[str, ...],
        operation: CompatibilityOperation,
    ) -> None:
        self.expected_lock_id = expected_lock_id
        self.actual_lock_id = actual_lock_id
        self.mismatches = mismatches
        self.operation = operation
        self.remediation = (
            "rebuild the index with the active embedding model lock or load the "
            "exact lock used to build the existing index"
        )
        fields = ", ".join(mismatches)
        super().__init__(
            f"embedding model lock mismatch during {operation}: {fields}; "
            f"{self.remediation}"
        )


@dataclass(frozen=True, slots=True)
class EmbeddingModelLock:
    """A complete model profile bound to exact artifacts and library versions."""

    profile: EmbeddingProfile
    artifacts: tuple[ArtifactDigest, ...]
    library_versions: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        paths = tuple(artifact.path for artifact in self.artifacts)
        if paths != tuple(sorted(set(paths))):
            raise ValueError("embedding lock artifacts must be unique and ordered")
        if set(paths) != set(self.profile.required_artifacts):
            raise ValueError("embedding lock does not bind every required artifact")
        if self.library_versions != tuple(sorted(set(self.library_versions))) or any(
            not name or not version for name, version in self.library_versions
        ):
            raise ValueError("embedding library versions must be complete and ordered")

    @property
    def lock_id(self) -> str:
        return _sha256_identity(self.manifest_payload())

    def manifest_payload(self) -> dict[str, object]:
        return {
            "artifacts": [artifact.manifest() for artifact in self.artifacts],
            "library_versions": dict(self.library_versions),
            "profile": self.profile.manifest(),
            "schema_version": "bijux.canon.index.embedding_model_lock.v1",
        }

    def manifest(self) -> dict[str, object]:
        payload = self.manifest_payload()
        return {"lock_id": _sha256_identity(payload), **payload}

    def require_compatible(
        self,
        other: EmbeddingModelLock,
        *,
        operation: CompatibilityOperation = "execution",
    ) -> None:
        """Fail before build or query when any locked identity differs."""

        if self.lock_id == other.lock_id:
            return
        profile_fields: tuple[tuple[str, object, object], ...] = (
            ("provider", self.profile.provider, other.profile.provider),
            ("model", self.profile.model_id, other.profile.model_id),
            ("revision", self.profile.revision, other.profile.revision),
            ("dimension", self.profile.dimension, other.profile.dimension),
            ("dtype", self.profile.dtype, other.profile.dtype),
            (
                "normalization",
                self.profile.normalization,
                other.profile.normalization,
            ),
            ("pooling", self.profile.pooling, other.profile.pooling),
            (
                "tokenizer",
                (self.profile.tokenizer_id, self.profile.tokenizer_revision),
                (other.profile.tokenizer_id, other.profile.tokenizer_revision),
            ),
            (
                "device_policy",
                self.profile.device_policy,
                other.profile.device_policy,
            ),
            (
                "numeric_policy",
                self.profile.numeric_policy,
                other.profile.numeric_policy,
            ),
        )
        mismatches = tuple(
            name for name, expected, actual in profile_fields if expected != actual
        )
        if self.artifacts != other.artifacts:
            mismatches += ("artifacts",)
        if self.library_versions != other.library_versions:
            mismatches += ("library_versions",)
        raise EmbeddingModelMismatchError(
            expected_lock_id=self.lock_id,
            actual_lock_id=other.lock_id,
            mismatches=mismatches or ("profile",),
            operation=operation,
        )

    def validate_vector(self, vector: tuple[float, ...]) -> None:
        """Validate vector dimension, finiteness, and declared normalization."""

        if len(vector) != self.profile.dimension:
            raise ValueError("embedding vector dimension does not match model lock")
        if any(not math.isfinite(value) for value in vector):
            raise ValueError("embedding vector contains a non-finite value")
        if self.profile.normalization == "l2":
            norm = math.sqrt(sum(value * value for value in vector))
            if not math.isclose(norm, 1.0, rel_tol=1e-5, abs_tol=1e-6):
                raise ValueError("embedding vector is not L2-normalized")


LOCAL_MINILM_PROFILE = EmbeddingProfile(
    profile_id="local-minilm-384",
    provider_kind="local",
    provider="sentence-transformers",
    model_id="sentence-transformers/all-MiniLM-L6-v2",
    revision="1110a243fdf4706b3f48f1d95db1a4f5529b4d41",
    dimension=384,
    dtype="float32",
    normalization="l2",
    pooling="mean",
    tokenizer_id="sentence-transformers/all-MiniLM-L6-v2",
    tokenizer_revision="1110a243fdf4706b3f48f1d95db1a4f5529b4d41",
    license_expression="Apache-2.0",
    device_policy="cpu-default-explicit-accelerator",
    numeric_policy="finite-float32-l2",
    offline_policy="required",
    support_tier="production",
    required_artifacts=(
        "1_Pooling/config.json",
        "config.json",
        "config_sentence_transformers.json",
        "model.safetensors",
        "modules.json",
        "sentence_bert_config.json",
        "special_tokens_map.json",
        "tokenizer.json",
        "tokenizer_config.json",
        "vocab.txt",
    ),
)


__all__ = [
    "ArtifactDigest",
    "CompatibilityOperation",
    "EmbeddingModelLock",
    "EmbeddingModelMismatchError",
    "EmbeddingProfile",
    "LOCAL_MINILM_PROFILE",
    "OfflinePolicy",
    "ProviderKind",
    "SupportTier",
]
