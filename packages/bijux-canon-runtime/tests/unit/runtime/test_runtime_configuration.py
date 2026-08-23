# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from pathlib import Path

import pytest

from bijux_canon_runtime.application.runtime_configuration import (
    ConfigurationSource,
    RuntimeWorkspaceLayout,
    resolve_runtime_configuration,
)
from bijux_canon_runtime.core.errors import ConfigurationError


def test_configuration_precedence_and_origins_are_explicit() -> None:
    configuration = resolve_runtime_configuration(
        file_values={
            "database_path": "file.duckdb",
            "strict_determinism": False,
            "offline": True,
            "resource_budget": {"step_limit": 3, "token_limit": 40},
        },
        environment={
            "AGENTIC_FLOWS_DB_PATH": "legacy.duckdb",
            "AGENTIC_FLOWS_STRICT": "0",
            "BIJUX_CANON_RUNTIME_DB_PATH": "canonical.duckdb",
            "BIJUX_CANON_RUNTIME_EMBEDDING_MODEL_PATH": "models/minilm",
            "BIJUX_CANON_RUNTIME_STRICT": "1",
            "BIJUX_CANON_RUNTIME_STEP_LIMIT": "5",
            "BIJUX_CANON_RUNTIME_RETRIEVAL_INDEX_PATH": "index.msgpack",
            "BIJUX_CANON_RUNTIME_WORKING_ROOT": "workspace",
        },
        explicit={"database_path": Path("explicit.duckdb")},
    )

    assert configuration.database_path == Path("explicit.duckdb")
    assert configuration.strict_determinism is True
    assert configuration.resource_budget.step_limit == 5
    assert configuration.resource_budget.token_limit == 40
    assert configuration.retrieval_index_path == Path("index.msgpack")
    assert configuration.embedding_model_path == Path("models/minilm")
    assert configuration.working_root == Path("workspace")
    assert configuration.source_for("database_path") is ConfigurationSource.EXPLICIT
    assert (
        configuration.source_for("strict_determinism")
        is ConfigurationSource.ENVIRONMENT
    )
    assert configuration.source_for("token_limit") is ConfigurationSource.FILE


def test_configuration_rejects_unknown_and_invalid_budget_fields() -> None:
    with pytest.raises(ConfigurationError, match="unknown runtime configuration"):
        resolve_runtime_configuration(file_values={"surprise": True})
    with pytest.raises(ConfigurationError, match="step_limit must be zero or greater"):
        resolve_runtime_configuration(
            environment={"BIJUX_CANON_RUNTIME_STEP_LIMIT": "-1"}
        )


def test_offline_policy_affects_behavior_and_can_be_explicitly_relaxed() -> None:
    offline = resolve_runtime_configuration()
    with pytest.raises(ConfigurationError, match="forbids network operation"):
        offline.require_network("remote provider invocation")

    online = resolve_runtime_configuration(explicit={"offline": False})
    online.require_network("remote provider invocation")


def test_secret_reference_is_validated_and_redacted() -> None:
    configuration = resolve_runtime_configuration(
        environment={
            "BIJUX_CANON_RUNTIME_PROVIDER_API_KEY_REF": "RESEARCH_PROVIDER_KEY",
            "RESEARCH_PROVIDER_KEY": "sensitive-value",
        }
    )

    assert configuration.provider_api_key is not None
    assert configuration.provider_api_key.is_available(
        {"RESEARCH_PROVIDER_KEY": "sensitive-value"}
    )
    assert "sensitive-value" not in repr(configuration)
    assert "sensitive-value" not in repr(configuration.redacted_record())
    with pytest.raises(ConfigurationError, match="uppercase environment variable"):
        resolve_runtime_configuration(explicit={"provider_api_key_ref": "not-safe"})


def test_workspace_layout_resolves_every_runtime_authority(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    configuration = resolve_runtime_configuration(explicit={"working_root": workspace})

    layout = configuration.require_workspace_layout()

    assert layout == RuntimeWorkspaceLayout.resolve(
        working_root=workspace,
        database_path=None,
        model_root=None,
        index_root=None,
    )
    assert layout.root == workspace.resolve()
    assert layout.manifest_path == workspace / "workspace.json"
    assert layout.migration_ledger_path == workspace / "workspace-migrations.json"
    assert layout.cas_root == workspace / "cas"
    assert layout.database_path == workspace / "runtime.duckdb"
    assert layout.job_store_path == workspace / "jobs.sqlite"
    assert layout.model_root == workspace / "models" / "local"
    assert layout.model_lock_path == workspace / "models" / "local" / "model.lock.json"
    assert layout.index_root == workspace / "indexes"
    assert layout.active_generation_path == workspace / "indexes" / "active.json"
    assert layout.locks_root == workspace / "locks"
    assert layout.staging_root == workspace / "staging"
    assert layout.temporary_root == workspace / "process"
    assert layout.backup_root == workspace / "backups"
    assert layout.schema_version == "bijux.runtime.workspace-layout.v2"
    assert layout.workspace_version == 2
    assert len(layout.identity_sha256) == 64


def test_workspace_layout_normalizes_overrides_against_root(tmp_path: Path) -> None:
    configuration = resolve_runtime_configuration(
        explicit={
            "working_root": tmp_path / "workspace" / ".." / "workspace",
            "database_path": Path("state/metadata.duckdb"),
            "embedding_model_path": Path("models/locked"),
            "retrieval_index_path": Path("retrieval"),
        }
    )

    layout = configuration.require_workspace_layout()

    assert layout.database_path == (layout.root / "state" / "metadata.duckdb")
    assert layout.model_root == layout.root / "models" / "locked"
    assert layout.index_root == layout.root / "retrieval"
    equivalent = resolve_runtime_configuration(
        explicit={
            "working_root": layout.root,
            "database_path": layout.root / "state" / "metadata.duckdb",
            "embedding_model_path": layout.root / "models" / "locked",
            "retrieval_index_path": layout.root / "retrieval",
        }
    )
    changed = resolve_runtime_configuration(
        explicit={
            "working_root": layout.root,
            "retrieval_index_path": layout.root / "other-retrieval",
        }
    )
    assert configuration.identity_sha256 == equivalent.identity_sha256
    assert configuration.identity_sha256 != changed.identity_sha256
    assert configuration.redacted_record()["workspace_layout"] == layout.record()


def test_workspace_layout_rejects_role_collisions(tmp_path: Path) -> None:
    configuration = resolve_runtime_configuration(
        explicit={
            "working_root": tmp_path / "workspace",
            "embedding_model_path": Path("cas"),
        }
    )

    with pytest.raises(ConfigurationError, match="directory roles collide"):
        configuration.require_workspace_layout()

    overlapping = resolve_runtime_configuration(
        explicit={
            "working_root": tmp_path / "workspace",
            "retrieval_index_path": Path("cas/indexes"),
        }
    )
    with pytest.raises(ConfigurationError, match="directory roles overlap"):
        overlapping.require_workspace_layout()


def test_workspace_layout_requires_a_configured_root() -> None:
    configuration = resolve_runtime_configuration()

    assert configuration.workspace_layout is None
    with pytest.raises(ConfigurationError, match="working_root is required"):
        configuration.require_workspace_layout()
