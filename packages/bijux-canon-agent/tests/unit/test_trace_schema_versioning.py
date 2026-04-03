from __future__ import annotations

import pytest

import bijux_agent.tracing.schema_versioning as schema_versioning
from bijux_agent.tracing.schema_versioning import (
    TRACE_SCHEMA_VERSION,
    TraceValidatorV2,
    assert_runtime_trace_compatibility,
    upgrade_trace,
    validate_trace_payload,
)


def test_upgrade_trace_adds_schema_version() -> None:
    raw = {"run_id": "run-1", "entries": [{"agent_id": "a"}]}
    upgraded = upgrade_trace(raw)
    assert upgraded["trace_schema_version"] == TRACE_SCHEMA_VERSION
    validate_trace_payload(upgraded)
    TraceValidatorV2.validate(upgraded)


def test_upgrade_rejects_unknown_future_version() -> None:
    raw = {
        "run_id": "run-1",
        "entries": [{"agent_id": "a"}],
        "trace_schema_version": TRACE_SCHEMA_VERSION + 5,
    }
    with pytest.raises(RuntimeError, match="newer than supported"):
        upgrade_trace(raw)


def test_validate_rejects_unversioned_payload() -> None:
    raw = {"run_id": "run-1", "entries": [{"agent_id": "a"}]}
    with pytest.raises(RuntimeError, match="Trace schema version mismatch"):
        validate_trace_payload(raw)


def test_runtime_guard_rejects_old_package(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(schema_versioning.metadata, "version", lambda _: "0.0.9")
    with pytest.raises(RuntimeError, match="runtime too old"):
        assert_runtime_trace_compatibility(TRACE_SCHEMA_VERSION)
