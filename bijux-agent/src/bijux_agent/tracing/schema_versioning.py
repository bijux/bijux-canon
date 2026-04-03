"""Trace schema versioning, validation, and migration helpers."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import metadata
from typing import Any

from packaging.version import InvalidVersion, Version

from bijux_agent.tracing.trace import TRACE_SCHEMA_VERSION


@dataclass(frozen=True)
class TraceValidatorV1:
    """Validate v1 trace payloads (no schema version)."""

    @staticmethod
    def validate(raw: dict[str, Any]) -> None:
        if "run_id" not in raw:
            raise RuntimeError("Trace missing run_id")
        entries = raw.get("entries")
        if not isinstance(entries, list) or not entries:
            raise RuntimeError("Trace must contain at least one entry")


@dataclass(frozen=True)
class TraceValidatorV2:
    """Validate v2 trace payloads with explicit schema version."""

    @staticmethod
    def validate(raw: dict[str, Any]) -> None:
        if raw.get("trace_schema_version") != TRACE_SCHEMA_VERSION:
            raise RuntimeError("Trace schema version mismatch")
        if "run_id" not in raw:
            raise RuntimeError("Trace missing run_id")
        entries = raw.get("entries")
        if not isinstance(entries, list) or not entries:
            raise RuntimeError("Trace must contain at least one entry")


def get_trace_schema_version(raw: dict[str, Any]) -> int:
    version = raw.get("trace_schema_version")
    if version is None:
        return 1
    if not isinstance(version, int):
        raise RuntimeError("Trace schema version must be an integer")
    return version


def upgrade_trace(raw: dict[str, Any]) -> dict[str, Any]:
    """Upgrade trace payloads to the current schema version."""
    version = get_trace_schema_version(raw)
    if version == TRACE_SCHEMA_VERSION:
        return raw
    if version > TRACE_SCHEMA_VERSION:
        raise RuntimeError(
            f"Trace schema version {version} is newer than supported "
            f"{TRACE_SCHEMA_VERSION}"
        )
    upgraded = dict(raw)
    if version == 1:
        upgraded["trace_schema_version"] = TRACE_SCHEMA_VERSION
        TraceValidatorV1.validate(upgraded)
        return upgraded
    raise RuntimeError(f"Trace schema version {version} not supported for upgrade")


def validate_trace_payload(raw: dict[str, Any]) -> None:
    version = get_trace_schema_version(raw)
    assert_runtime_trace_compatibility(version)
    if version == TRACE_SCHEMA_VERSION:
        TraceValidatorV2.validate(raw)
        return
    raise RuntimeError(f"Trace schema version {version} not supported")


_TRACE_SCHEMA_MIN_VERSION: dict[int, Version] = {
    TRACE_SCHEMA_VERSION: Version("0.1.0rc1"),
}


def _package_version() -> Version:
    try:
        raw_version = metadata.version("bijux-agent")
    except metadata.PackageNotFoundError as exc:  # pragma: no cover - env issue
        raise RuntimeError("bijux-agent package version not found") from exc
    try:
        return Version(raw_version)
    except InvalidVersion as exc:  # pragma: no cover - env issue
        raise RuntimeError(f"Invalid bijux-agent version: {raw_version}") from exc


def assert_runtime_trace_compatibility(trace_schema_version: int | None = None) -> None:
    """Fail fast when trace schema and runtime package versions are incompatible."""
    schema_version = trace_schema_version or TRACE_SCHEMA_VERSION
    if schema_version != TRACE_SCHEMA_VERSION:
        raise RuntimeError(
            "Trace schema version mismatch: "
            f"{schema_version} vs runtime {TRACE_SCHEMA_VERSION}"
        )
    minimum = _TRACE_SCHEMA_MIN_VERSION.get(schema_version)
    if minimum is None:
        raise RuntimeError(f"No runtime support for trace schema {schema_version}")
    if _package_version() < minimum:
        raise RuntimeError(
            "bijux-agent runtime too old for trace schema "
            f"{schema_version} (min {minimum})"
        )
