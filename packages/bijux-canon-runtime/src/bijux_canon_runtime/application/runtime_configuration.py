# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Validated configuration authority for runtime composition surfaces."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
import re
from typing import cast

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


@dataclass(frozen=True)
class RuntimeConfiguration:
    """Validated behavior-affecting runtime configuration."""

    database_path: Path | None
    retrieval_index_path: Path | None
    working_root: Path | None
    strict_determinism: bool
    offline: bool
    resource_budget: ExecutionBudget
    provider_api_key: SecretReference | None
    origins: tuple[tuple[str, ConfigurationSource], ...]

    def __post_init__(self) -> None:
        """Enforce configuration invariants at the ownership boundary."""
        if self.database_path is not None and not str(self.database_path):
            raise ConfigurationError("database_path must not be empty")
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
            "database_path": str(self.database_path) if self.database_path else None,
            "retrieval_index_path": (
                str(self.retrieval_index_path) if self.retrieval_index_path else None
            ),
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
    "retrieval_index_path",
    "working_root",
    "strict_determinism",
    "offline",
    "provider_api_key_ref",
    *_BUDGET_FIELDS,
}
_CANONICAL_ENVIRONMENT = {
    "database_path": "BIJUX_CANON_RUNTIME_DB_PATH",
    "retrieval_index_path": "BIJUX_CANON_RUNTIME_RETRIEVAL_INDEX_PATH",
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
        "retrieval_index_path",
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
    if field_name in {"database_path", "retrieval_index_path", "working_root"}:
        if value is None:
            return None
        if not isinstance(value, (str, Path)) or not str(value).strip():
            raise ConfigurationError("database_path must be a non-empty path")
        return Path(value)
    if field_name == "provider_api_key_ref":
        if value is None:
            return None
        if not isinstance(value, str):
            raise ConfigurationError("provider_api_key_ref must be a string")
        return SecretReference(value)
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
        "retrieval_index_path": None,
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
    retrieval_index_path = values["retrieval_index_path"]
    working_root = values["working_root"]
    provider_api_key = values["provider_api_key_ref"]
    return RuntimeConfiguration(
        database_path=database_path if isinstance(database_path, Path) else None,
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
    )


__all__ = [
    "ConfigurationSource",
    "RuntimeConfiguration",
    "SecretReference",
    "resolve_runtime_configuration",
]
