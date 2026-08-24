# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from pathlib import Path

import pytest

from bijux_canon_index.application import model_lifecycle
from bijux_canon_index.application.model_lifecycle import (
    MODEL_RECORD_NAME,
    ModelLifecycleError,
    load_model_record,
    register_existing_model,
    validate_model,
)
from bijux_canon_index.domain.embedding import LOCAL_MINILM_PROFILE
from bijux_canon_index.infra.embeddings.model_cache import (
    ModelMaterializationError,
    register_model,
)


class _Encoded(list[list[float]]):
    dtype = "float32"


class _Model:
    def __init__(self, dimension: int = LOCAL_MINILM_PROFILE.dimension) -> None:
        self.dimension = dimension

    def encode(self, _texts: list[str], **_options: object) -> _Encoded:
        value = 1.0 / (self.dimension**0.5)
        return _Encoded([[value] * self.dimension])


def _model_files(root: Path) -> None:
    root.mkdir(exist_ok=True)
    for relative_path in LOCAL_MINILM_PROFILE.required_artifacts:
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"validated:{relative_path}".encode())


def _versions() -> tuple[tuple[str, str], ...]:
    return (
        ("bijux-canon-index", "0.4.0"),
        ("numpy", "2.0.0"),
        ("python", "3.11.0"),
        ("sentence-transformers", "5.1.0"),
        ("torch", "2.7.0"),
    )


def _compatible_versions(monkeypatch: pytest.MonkeyPatch) -> None:
    versions = dict(_versions())
    monkeypatch.setattr(
        model_lifecycle.importlib.metadata,
        "version",
        lambda name: versions[name],
    )
    monkeypatch.setattr(model_lifecycle.platform, "python_version", lambda: "3.11.9")


def test_registration_records_pinned_source_files_license_and_cpu_validation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _model_files(tmp_path)
    _compatible_versions(monkeypatch)
    lock = register_model(
        LOCAL_MINILM_PROFILE,
        tmp_path,
        library_versions=_versions(),
    )
    monkeypatch.setattr(model_lifecycle, "_PINNED_ARTIFACTS", lock.artifacts)

    record = validate_model(tmp_path, loader=lambda *_: _Model())
    loaded = load_model_record(tmp_path / MODEL_RECORD_NAME)

    assert loaded == record
    assert record.model_lock_artifact_id == lock.lock_id
    assert record.source.endswith(LOCAL_MINILM_PROFILE.revision)
    assert record.license_expression == "Apache-2.0"
    assert record.license_pointer.startswith("https://huggingface.co/")
    assert record.dimension == 384
    assert record.compatibility.status == "compatible"
    assert record.validation_result == "passed"
    assert record.offline_reuse
    assert len(record.local_files) == len(LOCAL_MINILM_PROFILE.required_artifacts)
    assert record.record()["record_id"].startswith("sha256:")
    assert record.artifact_set_digest.startswith("sha256:")


def test_registration_refuses_incomplete_and_corrupt_models(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _model_files(tmp_path)
    missing = tmp_path / LOCAL_MINILM_PROFILE.required_artifacts[0]
    missing.unlink()
    with pytest.raises(ModelMaterializationError, match="missing required artifact"):
        register_model(
            LOCAL_MINILM_PROFILE,
            tmp_path,
            library_versions=_versions(),
        )

    missing.write_bytes(b"restored")
    lock = register_model(
        LOCAL_MINILM_PROFILE,
        tmp_path,
        library_versions=_versions(),
    )
    monkeypatch.setattr(model_lifecycle, "_PINNED_ARTIFACTS", lock.artifacts)
    missing.write_bytes(b"corrupt")
    with pytest.raises(ModelLifecycleError, match="corrupt"):
        validate_model(tmp_path, loader=lambda *_: _Model())


def test_validation_refuses_wrong_embedding_dimension(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _model_files(tmp_path)
    _compatible_versions(monkeypatch)
    lock = register_model(
        LOCAL_MINILM_PROFILE,
        tmp_path,
        library_versions=_versions(),
    )
    monkeypatch.setattr(model_lifecycle, "_PINNED_ARTIFACTS", lock.artifacts)

    with pytest.raises(ModelLifecycleError, match="dimension"):
        validate_model(tmp_path, loader=lambda *_: _Model(dimension=2))

    assert not (tmp_path / MODEL_RECORD_NAME).exists()


def test_validation_refuses_unavailable_embedding_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _model_files(tmp_path)
    lock = register_model(
        LOCAL_MINILM_PROFILE,
        tmp_path,
        library_versions=_versions(),
    )
    monkeypatch.setattr(model_lifecycle, "_PINNED_ARTIFACTS", lock.artifacts)

    def missing(name: str) -> str:
        raise model_lifecycle.importlib.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(model_lifecycle.importlib.metadata, "version", missing)
    with pytest.raises(ModelLifecycleError, match="unavailable"):
        validate_model(tmp_path, loader=lambda *_: _Model())


def test_validation_record_rejects_canonical_content_tampering(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _model_files(tmp_path)
    _compatible_versions(monkeypatch)
    lock = register_model(
        LOCAL_MINILM_PROFILE,
        tmp_path,
        library_versions=_versions(),
    )
    monkeypatch.setattr(model_lifecycle, "_PINNED_ARTIFACTS", lock.artifacts)
    validate_model(tmp_path, loader=lambda *_: _Model())
    record_path = tmp_path / MODEL_RECORD_NAME
    record_path.write_bytes(
        record_path.read_bytes().replace(
            b'"offline_reuse":true', b'"offline_reuse":false'
        )
    )

    with pytest.raises(ModelLifecycleError, match="record is invalid"):
        load_model_record(record_path)


def test_public_registration_refuses_files_not_from_the_pinned_revision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _model_files(tmp_path)
    _compatible_versions(monkeypatch)

    with pytest.raises(ModelMaterializationError, match="pinned revision"):
        register_existing_model(tmp_path)

    assert not (tmp_path / "model.lock.json").exists()
