# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Embedding model identity and compatibility contracts."""

from .model_lock import (
    ArtifactDigest,
    CompatibilityOperation,
    EmbeddingModelLock,
    EmbeddingModelMismatchError,
    EmbeddingProfile,
    LOCAL_MINILM_PROFILE,
)

__all__ = [
    "ArtifactDigest",
    "CompatibilityOperation",
    "EmbeddingModelLock",
    "EmbeddingModelMismatchError",
    "EmbeddingProfile",
    "LOCAL_MINILM_PROFILE",
]
