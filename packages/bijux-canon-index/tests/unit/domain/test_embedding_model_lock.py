# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from dataclasses import replace

import pytest

from bijux_canon_index.domain.embedding import (
    ArtifactDigest,
    EmbeddingModelLock,
    LOCAL_MINILM_PROFILE,
)


def _lock() -> EmbeddingModelLock:
    artifacts = tuple(
        ArtifactDigest(path, f"{index:064x}", index + 1)
        for index, path in enumerate(LOCAL_MINILM_PROFILE.required_artifacts, start=1)
    )
    return EmbeddingModelLock(
        LOCAL_MINILM_PROFILE,
        artifacts,
        (("sentence-transformers", "5.1.0"), ("torch", "2.8.0")),
    )


def test_default_profile_binds_production_model_identity() -> None:
    manifest = LOCAL_MINILM_PROFILE.manifest()

    assert manifest["model_id"] == "sentence-transformers/all-MiniLM-L6-v2"
    assert manifest["revision"] == "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
    assert manifest["dimension"] == 384
    assert manifest["dtype"] == "float32"
    assert manifest["normalization"] == "l2"
    assert manifest["offline_policy"] == "required"
    assert manifest["license_expression"] == "Apache-2.0"


def test_lock_identity_binds_artifacts_and_libraries() -> None:
    lock = _lock()
    changed = replace(
        lock,
        library_versions=(("sentence-transformers", "5.1.1"), ("torch", "2.8.0")),
    )

    assert lock.lock_id == _lock().lock_id
    assert lock.lock_id != changed.lock_id
    with pytest.raises(ValueError, match="lock mismatch"):
        lock.require_compatible(changed)


def test_lock_rejects_missing_artifact_and_invalid_vectors() -> None:
    lock = _lock()

    with pytest.raises(ValueError, match="every required artifact"):
        replace(lock, artifacts=lock.artifacts[:-1])
    with pytest.raises(ValueError, match="dimension"):
        lock.validate_vector((1.0,))
    with pytest.raises(ValueError, match="L2-normalized"):
        lock.validate_vector((0.0,) * 384)
    vector = (1.0, *((0.0,) * 383))
    lock.validate_vector(vector)
