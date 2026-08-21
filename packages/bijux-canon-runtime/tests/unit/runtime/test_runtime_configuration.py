# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from pathlib import Path

import pytest

from bijux_canon_runtime.application.runtime_configuration import (
    ConfigurationSource,
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
