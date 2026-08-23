# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Validated configuration authority for runtime composition surfaces."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
import hashlib
from itertools import combinations
import json
from pathlib import Path
import re
from typing import cast

from bijux_canon_index.application import CONTENT_EVIDENCE_RETRIEVAL_POLICY_ID

from bijux_canon_runtime.core.errors import ConfigurationError
from bijux_canon_runtime.runtime.budget import ExecutionBudget


class ConfigurationSource(StrEnum):
    """Stable configuration precedence sources, ordered from weak to strong."""

    DEFAULT = "default"
    FILE = "file"
    LEGACY_ENVIRONMENT = "legacy_environment"
    ENVIRONMENT = "environment"
    EXPLICIT = "explicit"


@dataclass(frozen=True)
class SecretReference:
    """Reference a secret by environment variable without retaining its value."""

    environment_variable: str

    def __post_init__(self) -> None:
        """Reject names that cannot be safely and predictably resolved."""
        if re.fullmatch(r"[A-Z][A-Z0-9_]*", self.environment_variable) is None:
            raise ConfigurationError(
                "secret reference must be an uppercase environment variable name"
            )

    def is_available(self, environment: Mapping[str, str]) -> bool:
        """Report availability without reading the secret into configuration state."""
        return bool(environment.get(self.environment_variable))


def _record_sha256(record: Mapping[str, object]) -> str:
    payload = json.dumps(
        record,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _effective_path(root: Path, configured: Path | None, default: Path) -> Path:
    candidate = default if configured is None else configured.expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    return candidate.resolve()


@dataclass(frozen=True)
class RuntimeWorkspaceLayout:
    """Versioned effective paths for one isolated Runtime workspace."""

    root: Path
    manifest_path: Path
    migration_ledger_path: Path
    cas_root: Path
    database_path: Path
    job_store_path: Path
    model_root: Path
    model_lock_path: Path
    index_root: Path
    active_generation_path: Path
    operations_root: Path
    vex_root: Path
    locks_root: Path
    staging_root: Path
    temporary_root: Path
    backup_root: Path
    schema_version: str = "bijux.runtime.workspace-layout.v4"
    workspace_version: int = 4

    @classmethod
    def resolve(
        cls,
        *,
        working_root: Path,
        database_path: Path | None,
        model_root: Path | None,
        index_root: Path | None,
    ) -> RuntimeWorkspaceLayout:
        """Resolve defaults and explicit overrides without touching the filesystem."""
        root = working_root.expanduser().resolve()
        cas_root = (root / "cas").resolve()
        database = _effective_path(root, database_path, root / "runtime.duckdb")
        jobs = (root / "jobs.sqlite").resolve()
        model = _effective_path(root, model_root, root / "models" / "local")
        index = _effective_path(root, index_root, root / "indexes")
        directory_roles = {
            "cas_root": cas_root,
            "index_root": index,
            "model_root": model,
            "operations_root": (root / "operations").resolve(),
            "vex_root": (root / "vex").resolve(),
            "locks_root": (root / "locks").resolve(),
            "staging_root": (root / "staging").resolve(),
            "temporary_root": (root / "process").resolve(),
            "backup_root": (root / "backups").resolve(),
        }
        collisions: dict[Path, list[str]] = {}
        for role, path in directory_roles.items():
            collisions.setdefault(path, []).append(role)
        duplicate_roles = next(
            (roles for roles in collisions.values() if len(roles) > 1),
            None,
        )
        if duplicate_roles is not None:
            raise ConfigurationError(
                "runtime workspace directory roles collide: "
                + ", ".join(sorted(duplicate_roles))
            )
        for (left_role, left), (right_role, right) in combinations(
            directory_roles.items(),
            2,
        ):
            if left in right.parents or right in left.parents:
                raise ConfigurationError(
                    "runtime workspace directory roles overlap: "
                    f"{left_role}, {right_role}"
                )
        if database == jobs:
            raise ConfigurationError("runtime database and job store paths collide")
        for role, directory in directory_roles.items():
            if (
                database == directory
                or directory in database.parents
                or jobs == directory
                or directory in jobs.parents
            ):
                raise ConfigurationError(
                    f"runtime state file collides with workspace directory: {role}"
                )
        return cls(
            root=root,
            manifest_path=root / "workspace.json",
            migration_ledger_path=root / "workspace-migrations.json",
            cas_root=cas_root,
            database_path=database,
            job_store_path=jobs,
            model_root=model,
            model_lock_path=model / "model.lock.json",
            index_root=index,
            active_generation_path=index / "active.json",
            operations_root=directory_roles["operations_root"],
            vex_root=directory_roles["vex_root"],
            locks_root=directory_roles["locks_root"],
            staging_root=directory_roles["staging_root"],
            temporary_root=directory_roles["temporary_root"],
            backup_root=directory_roles["backup_root"],
        )

    @property
    def identity_sha256(self) -> str:
        """Return the deterministic identity of this effective layout."""
        return _record_sha256(self.record(include_identity=False))

    def record(self, *, include_identity: bool = True) -> dict[str, object]:
        """Return a stable JSON-compatible representation."""
        record: dict[str, object] = {
            "active_generation_path": str(self.active_generation_path),
            "backup_root": str(self.backup_root),
            "cas_root": str(self.cas_root),
            "database_path": str(self.database_path),
            "index_root": str(self.index_root),
            "job_store_path": str(self.job_store_path),
            "locks_root": str(self.locks_root),
            "manifest_path": str(self.manifest_path),
            "migration_ledger_path": str(self.migration_ledger_path),
            "model_lock_path": str(self.model_lock_path),
            "model_root": str(self.model_root),
            "operations_root": str(self.operations_root),
            "root": str(self.root),
            "schema_version": self.schema_version,
            "staging_root": str(self.staging_root),
            "temporary_root": str(self.temporary_root),
            "vex_root": str(self.vex_root),
            "workspace_version": self.workspace_version,
        }
        if include_identity:
            record["identity_sha256"] = self.identity_sha256
        return record


@dataclass(frozen=True)
class RuntimeConfiguration:
    """Validated behavior-affecting runtime configuration."""

    database_path: Path | None
    embedding_model_path: Path | None
    retrieval_index_path: Path | None
    working_root: Path | None
    strict_determinism: bool
    offline: bool
    resource_budget: ExecutionBudget
    provider_api_key: SecretReference | None
    origins: tuple[tuple[str, ConfigurationSource], ...]
    retrieval_policy_id: str = CONTENT_EVIDENCE_RETRIEVAL_POLICY_ID

    @property
    def schema_version(self) -> str:
        """Return the effective configuration schema identity."""
        return "bijux.runtime.effective-configuration.v1"

    @property
    def workspace_layout(self) -> RuntimeWorkspaceLayout | None:
        """Resolve the sole workspace path authority when a root is configured."""
        if self.working_root is None:
            return None
        return RuntimeWorkspaceLayout.resolve(
            working_root=self.working_root,
            database_path=self.database_path,
            model_root=self.embedding_model_path,
            index_root=self.retrieval_index_path,
        )

    def require_workspace_layout(self) -> RuntimeWorkspaceLayout:
        """Return the effective workspace or fail with actionable configuration."""
        layout = self.workspace_layout
        if layout is None:
            raise ConfigurationError(
                "working_root is required to resolve the Runtime workspace layout"
            )
        return layout

    @property
    def identity_sha256(self) -> str:
        """Return a deterministic identity for behavior-affecting configuration."""
        return _record_sha256(self._identity_record())

    def __post_init__(self) -> None:
        """Enforce configuration invariants at the ownership boundary."""
        if self.database_path is not None and not str(self.database_path):
            raise ConfigurationError("database_path must not be empty")
        if not self.retrieval_policy_id.strip():
            raise ConfigurationError("retrieval_policy_id must not be empty")
        for field_name in _BUDGET_FIELDS:
            value = getattr(self.resource_budget, field_name)
            if value is not None and value < 0:
                raise ConfigurationError(f"{field_name} must be zero or greater")
        origin_names = [name for name, _ in self.origins]
        if len(origin_names) != len(set(origin_names)):
            raise ConfigurationError("configuration origins must be unique")

    def source_for(self, field_name: str) -> ConfigurationSource:
        """Return the winning source for one normalized configuration field."""
        try:
            return dict(self.origins)[field_name]
        except KeyError as exc:
            raise ConfigurationError(
                f"unknown normalized configuration field: {field_name}"
            ) from exc

    def require_network(self, operation: str) -> None:
        """Reject a network operation when the configured profile is offline."""
        if self.offline:
            raise ConfigurationError(
                f"offline runtime configuration forbids network operation: {operation}"
            )

    def redacted_record(self) -> dict[str, object]:
        """Return auditable settings without resolving or exposing secret values."""
        return {
            "schema_version": self.schema_version,
            "identity_sha256": self.identity_sha256,
            "database_path": str(self.database_path) if self.database_path else None,
            "embedding_model_path": (
                str(self.embedding_model_path) if self.embedding_model_path else None
            ),
            "retrieval_index_path": (
                str(self.retrieval_index_path) if self.retrieval_index_path else None
            ),
            "retrieval_policy_id": self.retrieval_policy_id,
            "working_root": str(self.working_root) if self.working_root else None,
            "strict_determinism": self.strict_determinism,
            "offline": self.offline,
            "resource_budget": {
                field_name: getattr(self.resource_budget, field_name)
                for field_name in _BUDGET_FIELDS
            },
            "provider_api_key_ref": (
                self.provider_api_key.environment_variable
                if self.provider_api_key is not None
                else None
            ),
            "origins": {name: source.value for name, source in self.origins},
            "workspace_layout": (
                None
                if self.workspace_layout is None
                else self.workspace_layout.record()
            ),
        }

    def _identity_record(self) -> dict[str, object]:
        layout = self.workspace_layout
        return {
            "offline": self.offline,
            "provider_api_key_ref": (
                self.provider_api_key.environment_variable
                if self.provider_api_key is not None
                else None
            ),
            "resource_budget": {
                field_name: getattr(self.resource_budget, field_name)
                for field_name in _BUDGET_FIELDS
            },
            "schema_version": self.schema_version,
            "strict_determinism": self.strict_determinism,
            "retrieval_policy_id": self.retrieval_policy_id,
            "workspace_layout": None if layout is None else layout.record(),
        }


_BUDGET_FIELDS = (
    "step_limit",
    "token_limit",
    "artifact_limit",
    "artifact_step_limit",
    "evidence_limit",
    "trace_event_limit",
)
_FIELDS = {
    "database_path",
    "embedding_model_path",
    "retrieval_index_path",
    "retrieval_policy_id",
    "working_root",
    "strict_determinism",
    "offline",
    "provider_api_key_ref",
    *_BUDGET_FIELDS,
}
_CANONICAL_ENVIRONMENT = {
    "database_path": "BIJUX_CANON_RUNTIME_DB_PATH",
    "embedding_model_path": "BIJUX_CANON_RUNTIME_EMBEDDING_MODEL_PATH",
    "retrieval_index_path": "BIJUX_CANON_RUNTIME_RETRIEVAL_INDEX_PATH",
    "retrieval_policy_id": "BIJUX_CANON_RUNTIME_RETRIEVAL_POLICY_ID",
    "working_root": "BIJUX_CANON_RUNTIME_WORKING_ROOT",
    "strict_determinism": "BIJUX_CANON_RUNTIME_STRICT",
    "offline": "BIJUX_CANON_RUNTIME_OFFLINE",
    "provider_api_key_ref": "BIJUX_CANON_RUNTIME_PROVIDER_API_KEY_REF",
    "step_limit": "BIJUX_CANON_RUNTIME_STEP_LIMIT",
    "token_limit": "BIJUX_CANON_RUNTIME_TOKEN_LIMIT",
    "artifact_limit": "BIJUX_CANON_RUNTIME_ARTIFACT_LIMIT",
    "artifact_step_limit": "BIJUX_CANON_RUNTIME_ARTIFACT_STEP_LIMIT",
    "evidence_limit": "BIJUX_CANON_RUNTIME_EVIDENCE_LIMIT",
    "trace_event_limit": "BIJUX_CANON_RUNTIME_TRACE_EVENT_LIMIT",
}
_LEGACY_ENVIRONMENT = {
    "database_path": "AGENTIC_FLOWS_DB_PATH",
    "strict_determinism": "AGENTIC_FLOWS_STRICT",
}


def _normalize_file_values(values: Mapping[str, object]) -> dict[str, object]:
    allowed = {
        "database_path",
        "embedding_model_path",
        "retrieval_index_path",
        "retrieval_policy_id",
        "working_root",
        "strict_determinism",
        "offline",
        "provider_api_key_ref",
        "resource_budget",
    }
    unknown = sorted(set(values) - allowed)
    if unknown:
        raise ConfigurationError(
            f"unknown runtime configuration fields: {', '.join(unknown)}"
        )
    normalized = {
        key: value for key, value in values.items() if key != "resource_budget"
    }
    budget = values.get("resource_budget", {})
    if not isinstance(budget, Mapping):
        raise ConfigurationError("resource_budget must be an object")
    unknown_budget = sorted(set(budget) - set(_BUDGET_FIELDS))
    if unknown_budget:
        raise ConfigurationError(
            f"unknown resource budget fields: {', '.join(unknown_budget)}"
        )
    normalized.update(budget)
    return normalized


def _parse_bool(field_name: str, value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    raise ConfigurationError(f"{field_name} must be a boolean")


def _parse_optional_int(field_name: str, value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ConfigurationError(f"{field_name} must be an integer")
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = int(value)
        except ValueError as exc:
            raise ConfigurationError(f"{field_name} must be an integer") from exc
    else:
        raise ConfigurationError(f"{field_name} must be an integer")
    if parsed < 0:
        raise ConfigurationError(f"{field_name} must be zero or greater")
    return parsed


def _normalized_value(field_name: str, value: object) -> object:
    if field_name in {"strict_determinism", "offline"}:
        return _parse_bool(field_name, value)
    if field_name in _BUDGET_FIELDS:
        return _parse_optional_int(field_name, value)
    if field_name in {
        "database_path",
        "embedding_model_path",
        "retrieval_index_path",
        "working_root",
    }:
        if value is None:
            return None
        if not isinstance(value, (str, Path)) or not str(value).strip():
            raise ConfigurationError(f"{field_name} must be a non-empty path")
        return Path(value)
    if field_name == "provider_api_key_ref":
        if value is None:
            return None
        if not isinstance(value, str):
            raise ConfigurationError("provider_api_key_ref must be a string")
        return SecretReference(value)
    if field_name == "retrieval_policy_id":
        if not isinstance(value, str) or not value.strip():
            raise ConfigurationError("retrieval_policy_id must be a non-empty string")
        return value
    raise ConfigurationError(f"unknown normalized configuration field: {field_name}")


def resolve_runtime_configuration(
    *,
    file_values: Mapping[str, object] | None = None,
    environment: Mapping[str, str] | None = None,
    explicit: Mapping[str, object] | None = None,
) -> RuntimeConfiguration:
    """Resolve and validate configuration with explicit, recorded precedence."""
    values: dict[str, object] = {
        "database_path": None,
        "embedding_model_path": None,
        "retrieval_index_path": None,
        "retrieval_policy_id": CONTENT_EVIDENCE_RETRIEVAL_POLICY_ID,
        "working_root": None,
        "strict_determinism": False,
        "offline": True,
        "provider_api_key_ref": None,
        **dict.fromkeys(_BUDGET_FIELDS),
    }
    origins = dict.fromkeys(_FIELDS, ConfigurationSource.DEFAULT)

    def apply(layer: Mapping[str, object], source: ConfigurationSource) -> None:
        unknown = sorted(set(layer) - _FIELDS)
        if unknown:
            raise ConfigurationError(
                f"unknown runtime configuration fields: {', '.join(unknown)}"
            )
        for field_name, raw_value in layer.items():
            values[field_name] = _normalized_value(field_name, raw_value)
            origins[field_name] = source

    if file_values is not None:
        apply(_normalize_file_values(file_values), ConfigurationSource.FILE)
    environment = environment or {}
    apply(
        {
            field_name: environment[variable]
            for field_name, variable in _LEGACY_ENVIRONMENT.items()
            if variable in environment
        },
        ConfigurationSource.LEGACY_ENVIRONMENT,
    )
    apply(
        {
            field_name: environment[variable]
            for field_name, variable in _CANONICAL_ENVIRONMENT.items()
            if variable in environment
        },
        ConfigurationSource.ENVIRONMENT,
    )
    if explicit is not None:
        apply(explicit, ConfigurationSource.EXPLICIT)

    budget = ExecutionBudget(
        step_limit=cast(int | None, values["step_limit"]),
        token_limit=cast(int | None, values["token_limit"]),
        artifact_limit=cast(int | None, values["artifact_limit"]),
        artifact_step_limit=cast(int | None, values["artifact_step_limit"]),
        evidence_limit=cast(int | None, values["evidence_limit"]),
        trace_event_limit=cast(int | None, values["trace_event_limit"]),
    )
    database_path = values["database_path"]
    embedding_model_path = values["embedding_model_path"]
    retrieval_index_path = values["retrieval_index_path"]
    working_root = values["working_root"]
    provider_api_key = values["provider_api_key_ref"]
    retrieval_policy_id = values["retrieval_policy_id"]
    return RuntimeConfiguration(
        database_path=database_path if isinstance(database_path, Path) else None,
        embedding_model_path=(
            embedding_model_path if isinstance(embedding_model_path, Path) else None
        ),
        retrieval_index_path=(
            retrieval_index_path if isinstance(retrieval_index_path, Path) else None
        ),
        working_root=working_root if isinstance(working_root, Path) else None,
        strict_determinism=bool(values["strict_determinism"]),
        offline=bool(values["offline"]),
        resource_budget=budget,
        provider_api_key=(
            provider_api_key if isinstance(provider_api_key, SecretReference) else None
        ),
        origins=tuple(sorted(origins.items())),
        retrieval_policy_id=str(retrieval_policy_id),
    )


__all__ = [
    "ConfigurationSource",
    "RuntimeConfiguration",
    "RuntimeWorkspaceLayout",
    "SecretReference",
    "resolve_runtime_configuration",
]
