# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from bijux_canon_index.domain.embedding import LOCAL_MINILM_PROFILE
from bijux_canon_index.infra.embeddings.model_cache import (
    ModelMaterializationError,
    load_model_lock,
    materialize_model,
    verify_materialized_model,
)
from bijux_canon_index.tooling import embedding_models


def _metadata() -> dict[str, object]:
    return {
        "sha": LOCAL_MINILM_PROFILE.revision,
        "cardData": {"license": "apache-2.0"},
        "siblings": [
            {"rfilename": path} for path in LOCAL_MINILM_PROFILE.required_artifacts
        ],
    }


def _write_valid_artifact(_url: str, destination: Path) -> None:
    destination.write_bytes(b"valid")


def test_materializes_verified_revision_addressed_offline_cache(
    tmp_path: Path,
) -> None:
    def fetch_artifact(url: str, destination: Path) -> None:
        destination.write_bytes(f"locked artifact from {url}".encode())

    lock = materialize_model(
        LOCAL_MINILM_PROFILE,
        tmp_path,
        library_versions=(("sentence-transformers", "5.1.0"),),
        metadata_fetcher=lambda _: _metadata(),
        artifact_fetcher=fetch_artifact,
    )
    model_root = (
        tmp_path / LOCAL_MINILM_PROFILE.profile_id / LOCAL_MINILM_PROFILE.revision
    )

    verify_materialized_model(model_root, lock)
    assert load_model_lock(model_root / "model.lock.json") == lock
    assert (model_root / "model.lock.json").is_file()
    assert len(lock.artifacts) == len(LOCAL_MINILM_PROFILE.required_artifacts)


def test_offline_verification_detects_corrupt_artifact(tmp_path: Path) -> None:
    lock = materialize_model(
        LOCAL_MINILM_PROFILE,
        tmp_path,
        library_versions=(("sentence-transformers", "5.1.0"),),
        metadata_fetcher=lambda _: _metadata(),
        artifact_fetcher=_write_valid_artifact,
    )
    model_root = (
        tmp_path / LOCAL_MINILM_PROFILE.profile_id / LOCAL_MINILM_PROFILE.revision
    )
    (model_root / lock.artifacts[0].path).write_bytes(b"corrupt")

    with pytest.raises(ModelMaterializationError, match="corrupt"):
        verify_materialized_model(model_root, lock)


def test_missing_artifact_provides_exact_materialization_command(
    tmp_path: Path,
) -> None:
    lock = materialize_model(
        LOCAL_MINILM_PROFILE,
        tmp_path,
        library_versions=(("sentence-transformers", "5.1.0"),),
        metadata_fetcher=lambda _: _metadata(),
        artifact_fetcher=_write_valid_artifact,
    )
    model_root = (
        tmp_path / LOCAL_MINILM_PROFILE.profile_id / LOCAL_MINILM_PROFILE.revision
    )
    (model_root / lock.artifacts[0].path).unlink()

    with pytest.raises(ModelMaterializationError, match="materialize with") as raised:
        verify_materialized_model(model_root, lock)

    assert raised.value.remediation_command == (
        sys.executable,
        "-m",
        "bijux_canon_index.tooling.embedding_models",
        "--profile",
        "local-minilm-384",
        "--cache-root",
        str(tmp_path),
    )


def test_materialization_rejects_wrong_revision(tmp_path: Path) -> None:
    metadata = _metadata()
    metadata["sha"] = "0" * 40

    with pytest.raises(ModelMaterializationError, match="revision"):
        materialize_model(
            LOCAL_MINILM_PROFILE,
            tmp_path,
            library_versions=(("sentence-transformers", "5.1.0"),),
            metadata_fetcher=lambda _: metadata,
        )


def test_materialization_command_emits_canonical_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest = {"lock_id": "sha256:locked", "schema_version": "test"}
    monkeypatch.setattr(
        embedding_models,
        "materialize_profile",
        lambda profile_id, cache_root: manifest,
    )

    result = embedding_models.main(
        ["--profile", "local-minilm-384", "--cache-root", str(tmp_path)]
    )

    assert result == 0
    assert json.loads(capsys.readouterr().out) == manifest
