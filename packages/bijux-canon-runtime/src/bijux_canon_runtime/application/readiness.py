# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Typed shallow liveness and deep Runtime readiness checks."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
import os
from pathlib import Path
import tempfile

from bijux_canon_index.application import IndexService

from bijux_canon_runtime.application.runtime_configuration import RuntimeConfiguration
from bijux_canon_runtime.observability.storage.execution_store import (
    DuckDBExecutionStore,
)
from bijux_canon_runtime.runtime.persistence import (
    AtomicFilesystemArtifactPayloadStore,
)


class ReadinessCheckName(StrEnum):
    """Stable dependency names reported to operators."""

    SCHEMA = "schema-migrations"
    ARTIFACT_STORE = "artifact-store"
    ACTIVE_GENERATION = "active-generation"
    MODEL = "model-configuration"
    PROVIDER = "provider-configuration"
    WRITABLE_STATE = "writable-state"


class ReadinessReason(StrEnum):
    """Safe machine-readable reasons for a degraded Runtime."""

    DATABASE_NOT_CONFIGURED = "database-not-configured"
    SCHEMA_UNAVAILABLE = "schema-unavailable"
    ARTIFACT_STORE_NOT_CONFIGURED = "artifact-store-not-configured"
    ARTIFACT_STORE_UNAVAILABLE = "artifact-store-unavailable"
    INDEX_NOT_CONFIGURED = "index-not-configured"
    ACTIVE_GENERATION_UNAVAILABLE = "active-generation-unavailable"
    MODEL_CONFIGURATION_UNAVAILABLE = "model-configuration-unavailable"
    PROVIDER_CONFIGURATION_UNAVAILABLE = "provider-configuration-unavailable"
    STATE_NOT_WRITABLE = "state-not-writable"


@dataclass(frozen=True, slots=True)
class LivenessReport:
    """A process-only signal that performs no dependency I/O."""

    schema_version: str = "bijux.runtime.liveness.v1"
    live: bool = True
    status: str = "ok"


@dataclass(frozen=True, slots=True)
class ReadinessCheck:
    """One typed readiness verdict without paths, secrets, or exception text."""

    name: ReadinessCheckName
    ready: bool
    reason: ReadinessReason | None
    remediation: str | None


@dataclass(frozen=True, slots=True)
class ReadinessReport:
    """Conjunctive readiness with every degraded reason retained."""

    schema_version: str
    ready: bool
    status: str
    checks: tuple[ReadinessCheck, ...]
    reasons: tuple[ReadinessReason, ...]


def runtime_liveness() -> LivenessReport:
    """Return process liveness without touching configuration or dependencies."""
    return LivenessReport()


class RuntimeReadinessService:
    """Verify every dependency required to accept production work."""

    def __init__(
        self,
        configuration: RuntimeConfiguration,
        *,
        environment: Mapping[str, str] | None = None,
    ) -> None:
        self._configuration = configuration
        self._environment = dict(environment or {})

    def evaluate(self) -> ReadinessReport:
        """Return all dependency verdicts without short-circuiting failures."""
        checks: list[ReadinessCheck] = []
        checks.append(self._schema_check())
        artifact_store, artifact_check = self._artifact_store_check()
        checks.append(artifact_check)
        generation, generation_check = self._active_generation_check()
        checks.append(generation_check)
        checks.append(self._model_check(generation))
        checks.append(self._provider_check())
        checks.append(self._writable_state_check(artifact_store))
        reasons = tuple(
            check.reason for check in checks if check.reason is not None
        )
        ready = not reasons
        return ReadinessReport(
            schema_version="bijux.runtime.readiness.v1",
            ready=ready,
            status="ready" if ready else "degraded",
            checks=tuple(checks),
            reasons=reasons,
        )

    def _schema_check(self) -> ReadinessCheck:
        database_path = self._configuration.database_path
        if database_path is None:
            return _degraded(
                ReadinessCheckName.SCHEMA,
                ReadinessReason.DATABASE_NOT_CONFIGURED,
                "Configure BIJUX_CANON_RUNTIME_DB_PATH.",
            )
        try:
            store = DuckDBExecutionStore(database_path)
            store.close()
        except Exception:
            return _degraded(
                ReadinessCheckName.SCHEMA,
                ReadinessReason.SCHEMA_UNAVAILABLE,
                "Apply Runtime migrations and verify database access.",
            )
        return _ready(ReadinessCheckName.SCHEMA)

    def _artifact_store_check(
        self,
    ) -> tuple[AtomicFilesystemArtifactPayloadStore | None, ReadinessCheck]:
        working_root = self._configuration.working_root
        if working_root is None:
            return None, _degraded(
                ReadinessCheckName.ARTIFACT_STORE,
                ReadinessReason.ARTIFACT_STORE_NOT_CONFIGURED,
                "Configure BIJUX_CANON_RUNTIME_WORKING_ROOT.",
            )
        try:
            store = AtomicFilesystemArtifactPayloadStore(working_root / "cas")
            next(store.iter_artifact_ids(), None)
        except Exception:
            return None, _degraded(
                ReadinessCheckName.ARTIFACT_STORE,
                ReadinessReason.ARTIFACT_STORE_UNAVAILABLE,
                "Repair or restore the configured Runtime artifact store.",
            )
        return store, _ready(ReadinessCheckName.ARTIFACT_STORE)

    def _active_generation_check(self) -> tuple[object | None, ReadinessCheck]:
        index_path = self._configuration.retrieval_index_path
        if index_path is None:
            return None, _degraded(
                ReadinessCheckName.ACTIVE_GENERATION,
                ReadinessReason.INDEX_NOT_CONFIGURED,
                "Configure BIJUX_CANON_RUNTIME_RETRIEVAL_INDEX_PATH.",
            )
        try:
            if not index_path.is_dir():
                raise FileNotFoundError("configured index registry is absent")
            report = IndexService(index_path).verify()
            if (
                report.integrity.status != "verified"
                or not report.activation.active
                or report.activation.active_generation_id != report.generation_id
            ):
                raise ValueError("active generation did not pass integrity checks")
        except Exception:
            return None, _degraded(
                ReadinessCheckName.ACTIVE_GENERATION,
                ReadinessReason.ACTIVE_GENERATION_UNAVAILABLE,
                "Activate a verified immutable index generation.",
            )
        return report, _ready(ReadinessCheckName.ACTIVE_GENERATION)

    @staticmethod
    def _model_check(generation: object | None) -> ReadinessCheck:
        dimension = getattr(generation, "dimension", None)
        if (
            generation is None
            or not getattr(generation, "model_lock_artifact_id", "")
            or isinstance(dimension, bool)
            or not isinstance(dimension, int)
            or dimension < 1
        ):
            return _degraded(
                ReadinessCheckName.MODEL,
                ReadinessReason.MODEL_CONFIGURATION_UNAVAILABLE,
                "Activate an index built with a verified model lock and dimension.",
            )
        return _ready(ReadinessCheckName.MODEL)

    def _provider_check(self) -> ReadinessCheck:
        if self._configuration.offline:
            return _ready(ReadinessCheckName.PROVIDER)
        reference = self._configuration.provider_api_key
        if reference is None or not reference.is_available(self._environment):
            return _degraded(
                ReadinessCheckName.PROVIDER,
                ReadinessReason.PROVIDER_CONFIGURATION_UNAVAILABLE,
                "Configure the selected provider credential reference.",
            )
        return _ready(ReadinessCheckName.PROVIDER)

    def _writable_state_check(
        self,
        artifact_store: AtomicFilesystemArtifactPayloadStore | None,
    ) -> ReadinessCheck:
        database_path = self._configuration.database_path
        if database_path is None or artifact_store is None:
            return _degraded(
                ReadinessCheckName.WRITABLE_STATE,
                ReadinessReason.STATE_NOT_WRITABLE,
                "Configure writable Runtime database and artifact roots.",
            )
        try:
            self._write_probe(database_path.parent)
            self._write_probe(artifact_store.root)
        except Exception:
            return _degraded(
                ReadinessCheckName.WRITABLE_STATE,
                ReadinessReason.STATE_NOT_WRITABLE,
                "Grant atomic write access to Runtime state roots.",
            )
        return _ready(ReadinessCheckName.WRITABLE_STATE)

    @staticmethod
    def _write_probe(root: Path) -> None:
        descriptor, name = tempfile.mkstemp(prefix=".readiness.", dir=root)
        try:
            os.write(descriptor, b"bijux-runtime-readiness\n")
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
            Path(name).unlink(missing_ok=True)


def runtime_store_is_ready(db_path: Path) -> bool:
    """Return whether the configured execution store can be opened and closed."""
    try:
        store = DuckDBExecutionStore(db_path)
        store.close()
    except Exception:
        return False
    return True


def _ready(name: ReadinessCheckName) -> ReadinessCheck:
    return ReadinessCheck(name=name, ready=True, reason=None, remediation=None)


def _degraded(
    name: ReadinessCheckName,
    reason: ReadinessReason,
    remediation: str,
) -> ReadinessCheck:
    return ReadinessCheck(
        name=name,
        ready=False,
        reason=reason,
        remediation=remediation,
    )


__all__ = [
    "LivenessReport",
    "ReadinessCheck",
    "ReadinessCheckName",
    "ReadinessReason",
    "ReadinessReport",
    "RuntimeReadinessService",
    "runtime_liveness",
    "runtime_store_is_ready",
]
