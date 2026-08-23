# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3

import duckdb
import pytest

from bijux_canon_index.domain.embedding import LOCAL_MINILM_PROFILE
from bijux_canon_index.infra.embeddings.model_cache import materialize_model
from bijux_canon_runtime.application import workspace_initialization
from bijux_canon_runtime.application.runtime_configuration import (
    resolve_runtime_configuration,
)
from bijux_canon_runtime.application.workspace_initialization import (
    WorkspaceInitializationError,
    WorkspaceInitializationErrorCode,
    WorkspaceInitializationStatus,
    initialize_runtime_workspace,
)
from bijux_canon_runtime.model.artifact import canonical_json_bytes


def _materialized_model(tmp_path: Path) -> Path:
    cache_root = tmp_path / "model-cache"
    metadata: dict[str, object] = {
        "sha": LOCAL_MINILM_PROFILE.revision,
        "cardData": {"license": "apache-2.0"},
        "siblings": [
            {"rfilename": path} for path in LOCAL_MINILM_PROFILE.required_artifacts
        ],
    }

    def fetch_artifact(_url: str, destination: Path) -> None:
        destination.write_bytes(b"valid")

    materialize_model(
        LOCAL_MINILM_PROFILE,
        cache_root,
        library_versions=(("sentence-transformers", "5.1.0"),),
        metadata_fetcher=lambda _url: metadata,
        artifact_fetcher=fetch_artifact,
    )
    return cache_root / LOCAL_MINILM_PROFILE.profile_id / LOCAL_MINILM_PROFILE.revision


def _configuration(workspace: Path, model: Path, **extra: object):
    return resolve_runtime_configuration(
        explicit={
            "embedding_model_path": model,
            "working_root": workspace,
            **extra,
        }
    )


def test_fresh_initialization_is_atomic_and_repeat_is_exact_noop(
    tmp_path: Path,
) -> None:
    model = _materialized_model(tmp_path)
    workspace = tmp_path / "workspace"
    configuration = _configuration(workspace, model)

    first = initialize_runtime_workspace(configuration)
    layout = configuration.require_workspace_layout()
    manifest_bytes = layout.manifest_path.read_bytes()
    state = {
        path.relative_to(workspace).as_posix(): path.stat().st_mtime_ns
        for path in workspace.rglob("*")
    }
    second = initialize_runtime_workspace(configuration)

    assert first.status is WorkspaceInitializationStatus.INITIALIZED
    assert second.status is WorkspaceInitializationStatus.UNCHANGED
    assert second.workspace_id == first.workspace_id
    assert second.model_lock_artifact_id == first.model_lock_artifact_id
    assert layout.manifest_path.read_bytes() == manifest_bytes
    assert {
        path.relative_to(workspace).as_posix(): path.stat().st_mtime_ns
        for path in workspace.rglob("*")
    } == state
    assert layout.database_path.is_file()
    assert layout.job_store_path.is_file()
    assert layout.cas_root.is_dir()
    assert layout.index_root.is_dir()
    assert not list(tmp_path.glob(".workspace.*.initializing"))


def test_existing_workspace_refuses_configuration_change_without_mutation(
    tmp_path: Path,
) -> None:
    model = _materialized_model(tmp_path)
    workspace = tmp_path / "workspace"
    original = _configuration(workspace, model)
    initialize_runtime_workspace(original)
    before = original.require_workspace_layout().manifest_path.read_bytes()

    with pytest.raises(WorkspaceInitializationError) as raised:
        initialize_runtime_workspace(_configuration(workspace, model, offline=False))

    assert (
        raised.value.code is WorkspaceInitializationErrorCode.INCOMPATIBLE_CONFIGURATION
    )
    assert original.require_workspace_layout().manifest_path.read_bytes() == before


def test_partial_workspace_is_refused_without_filling_missing_state(
    tmp_path: Path,
) -> None:
    model = _materialized_model(tmp_path)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    marker = workspace / "owned.txt"
    marker.write_text("preserve", encoding="utf-8")

    with pytest.raises(WorkspaceInitializationError) as raised:
        initialize_runtime_workspace(_configuration(workspace, model))

    assert raised.value.code is WorkspaceInitializationErrorCode.PARTIAL_WORKSPACE
    assert marker.read_text(encoding="utf-8") == "preserve"
    assert sorted(path.name for path in workspace.iterdir()) == ["owned.txt"]


def test_incompatible_workspace_version_is_typed_and_non_mutating(
    tmp_path: Path,
) -> None:
    model = _materialized_model(tmp_path)
    workspace = tmp_path / "workspace"
    configuration = _configuration(workspace, model)
    initialize_runtime_workspace(configuration)
    manifest_path = configuration.require_workspace_layout().manifest_path
    manifest = json.loads(manifest_path.read_bytes())
    manifest["workspace_version"] = 99
    changed = canonical_json_bytes(manifest)
    manifest_path.write_bytes(changed)

    with pytest.raises(WorkspaceInitializationError) as raised:
        initialize_runtime_workspace(configuration)

    assert raised.value.code is WorkspaceInitializationErrorCode.INCOMPATIBLE_VERSION
    assert manifest_path.read_bytes() == changed


def test_manifest_content_cannot_diverge_from_its_recorded_identity(
    tmp_path: Path,
) -> None:
    model = _materialized_model(tmp_path)
    workspace = tmp_path / "workspace"
    configuration = _configuration(workspace, model)
    initialize_runtime_workspace(configuration)
    manifest_path = configuration.require_workspace_layout().manifest_path
    manifest = json.loads(manifest_path.read_bytes())
    manifest["configuration"]["offline"] = False
    changed = canonical_json_bytes(manifest)
    manifest_path.write_bytes(changed)

    with pytest.raises(WorkspaceInitializationError) as raised:
        initialize_runtime_workspace(configuration)

    assert (
        raised.value.code is WorkspaceInitializationErrorCode.INCOMPATIBLE_CONFIGURATION
    )
    assert manifest_path.read_bytes() == changed


@pytest.mark.parametrize("store_kind", ["duckdb", "jobs"])
def test_corrupt_state_store_is_refused_without_repair(
    tmp_path: Path,
    store_kind: str,
) -> None:
    model = _materialized_model(tmp_path)
    workspace = tmp_path / "workspace"
    configuration = _configuration(workspace, model)
    initialize_runtime_workspace(configuration)
    layout = configuration.require_workspace_layout()
    if store_kind == "duckdb":
        with duckdb.connect(str(layout.database_path)) as connection:
            connection.execute(
                "UPDATE schema_migrations SET checksum = 'tampered' WHERE version = 1"
            )
        changed = layout.database_path.read_bytes()
    else:
        with sqlite3.connect(layout.job_store_path) as connection:
            connection.execute("DROP TABLE runtime_jobs")
        changed = layout.job_store_path.read_bytes()

    with pytest.raises(WorkspaceInitializationError) as raised:
        initialize_runtime_workspace(configuration)

    assert raised.value.code is WorkspaceInitializationErrorCode.CORRUPT_STATE
    changed_path = (
        layout.database_path if store_kind == "duckdb" else layout.job_store_path
    )
    assert changed_path.read_bytes() == changed


def test_missing_model_refuses_before_creating_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"

    with pytest.raises(WorkspaceInitializationError) as raised:
        initialize_runtime_workspace(
            _configuration(workspace, tmp_path / "missing-model")
        )

    assert raised.value.code is WorkspaceInitializationErrorCode.MODEL_UNAVAILABLE
    assert not workspace.exists()


def test_external_runtime_state_path_is_refused_without_side_effects(
    tmp_path: Path,
) -> None:
    model = _materialized_model(tmp_path)
    workspace = tmp_path / "workspace"
    database = tmp_path / "external" / "runtime.duckdb"

    with pytest.raises(WorkspaceInitializationError) as raised:
        initialize_runtime_workspace(
            _configuration(workspace, model, database_path=database)
        )

    assert raised.value.code is WorkspaceInitializationErrorCode.EXTERNAL_STATE_PATH
    assert not workspace.exists()
    assert not database.exists()


def test_activation_failure_removes_staging_and_leaves_no_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = _materialized_model(tmp_path)
    workspace = tmp_path / "workspace"

    def refuse_activation(_source: Path, _destination: Path) -> None:
        raise PermissionError("activation denied")

    monkeypatch.setattr(os, "rename", refuse_activation)

    with pytest.raises(WorkspaceInitializationError) as raised:
        initialize_runtime_workspace(_configuration(workspace, model))

    assert raised.value.code is WorkspaceInitializationErrorCode.UNWRITABLE
    assert not workspace.exists()
    assert not list(tmp_path.glob(".workspace.*.initializing"))


def test_workspace_root_symlink_is_refused_without_touching_target(
    tmp_path: Path,
) -> None:
    model = _materialized_model(tmp_path)
    target = tmp_path / "target"
    target.mkdir()
    workspace = tmp_path / "workspace"
    workspace.symlink_to(target, target_is_directory=True)

    with pytest.raises(WorkspaceInitializationError) as raised:
        initialize_runtime_workspace(_configuration(workspace, model))

    assert raised.value.code is WorkspaceInitializationErrorCode.UNSAFE_PATH
    assert list(target.iterdir()) == []


def test_initialization_failure_cleans_staging_after_constructor_crash(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = _materialized_model(tmp_path)
    workspace = tmp_path / "workspace"

    def crash(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise RuntimeError("simulated constructor crash")

    monkeypatch.setattr(workspace_initialization, "_initialize_staging", crash)

    with pytest.raises(RuntimeError, match="constructor crash"):
        initialize_runtime_workspace(_configuration(workspace, model))

    assert not workspace.exists()
    assert not list(tmp_path.glob(".workspace.*.initializing"))
