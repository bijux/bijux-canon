# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Typed shallow liveness and capability-aware Runtime readiness checks."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
import os
from pathlib import Path
import tempfile

from bijux_canon_index.application import IndexService
from bijux_canon_index.infra.embeddings.model_cache import (
    load_model_lock,
    verify_materialized_model,
)
from bijux_canon_runtime.application.runtime_configuration import (
    RuntimeConfiguration,
    RuntimeWorkspaceLayout,
)
from bijux_canon_runtime.application.workspace_initialization import (
    validate_runtime_workspace,
)
from bijux_canon_runtime.observability.storage.execution_store import (
    DuckDBExecutionStore,
)


class ReadinessCapability(StrEnum):
    """Public capability whose exact dependencies are being checked."""

    INITIALIZED = "initialized"
    INGEST = "ingest"
    INDEX = "index"
    RETRIEVE = "retrieve"
    ASK = "ask"
    RESEARCH = "research"
    RUN = "run"


class ReadinessCheckName(StrEnum):
    """Stable dependency names reported to operators."""

    WORKSPACE = "workspace-initialization"
    SCHEMA = "schema-migrations"
    ARTIFACT_STORE = "artifact-store"
    ACTIVE_GENERATION = "active-generation"
    MODEL = "model-configuration"
    PROVIDER = "provider-configuration"
    WRITABLE_STATE = "writable-state"


class ReadinessReason(StrEnum):
    """Safe machine-readable reasons for a degraded Runtime."""

    WORKSPACE_NOT_CONFIGURED = "workspace-not-configured"
    WORKSPACE_INVALID = "workspace-invalid"
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
    """Conjunctive readiness for one named public capability."""

    schema_version: str
    capability: ReadinessCapability
    ready: bool
    status: str
    checks: tuple[ReadinessCheck, ...]
    reasons: tuple[ReadinessReason, ...]


def runtime_liveness() -> LivenessReport:
    """Return process liveness without touching configuration or dependencies."""
    return LivenessReport()


_BASE_CHECKS = (
    ReadinessCheckName.WORKSPACE,
    ReadinessCheckName.SCHEMA,
    ReadinessCheckName.ARTIFACT_STORE,
    ReadinessCheckName.WRITABLE_STATE,
)
_CAPABILITY_CHECKS = {
    ReadinessCapability.INITIALIZED: _BASE_CHECKS,
    ReadinessCapability.INGEST: _BASE_CHECKS,
    ReadinessCapability.INDEX: (*_BASE_CHECKS, ReadinessCheckName.MODEL),
    ReadinessCapability.RETRIEVE: (
        *_BASE_CHECKS,
        ReadinessCheckName.ACTIVE_GENERATION,
        ReadinessCheckName.MODEL,
    ),
    ReadinessCapability.ASK: (
        *_BASE_CHECKS,
        ReadinessCheckName.ACTIVE_GENERATION,
        ReadinessCheckName.MODEL,
        ReadinessCheckName.PROVIDER,
    ),
    ReadinessCapability.RESEARCH: (
        *_BASE_CHECKS,
        ReadinessCheckName.ACTIVE_GENERATION,
        ReadinessCheckName.MODEL,
        ReadinessCheckName.PROVIDER,
    ),
    ReadinessCapability.RUN: (
        *_BASE_CHECKS,
        ReadinessCheckName.ACTIVE_GENERATION,
        ReadinessCheckName.MODEL,
        ReadinessCheckName.PROVIDER,
    ),
}


class RuntimeReadinessService:
    """Verify only the dependencies required by one public operation."""

    def __init__(
        self,
        configuration: RuntimeConfiguration,
        *,
        environment: Mapping[str, str] | None = None,
    ) -> None:
        self._configuration = configuration
        self._environment = dict(environment or {})

    def evaluate(
        self,
        capability: ReadinessCapability = ReadinessCapability.INITIALIZED,
    ) -> ReadinessReport:
        """Return all required dependency verdicts without hidden allocation."""
        if not isinstance(capability, ReadinessCapability):
            raise ValueError("readiness capability is unsupported")
        layout = self._configuration.workspace_layout
        generation: object | None = None
        checks: list[ReadinessCheck] = []
        for name in _CAPABILITY_CHECKS[capability]:
            if name is ReadinessCheckName.WORKSPACE:
                check = self._workspace_check(layout)
            elif name is ReadinessCheckName.SCHEMA:
                check = self._schema_check(layout)
            elif name is ReadinessCheckName.ARTIFACT_STORE:
                check = self._artifact_store_check(layout)
            elif name is ReadinessCheckName.WRITABLE_STATE:
                check = self._writable_state_check(layout)
            elif name is ReadinessCheckName.ACTIVE_GENERATION:
                generation, check = self._active_generation_check(layout)
            elif name is ReadinessCheckName.MODEL:
                check = self._model_check(layout, generation)
            else:
                check = self._provider_check()
            checks.append(check)
        reasons = tuple(check.reason for check in checks if check.reason is not None)
        ready = not reasons
        return ReadinessReport(
            schema_version="bijux.runtime.readiness.v2",
            capability=capability,
            ready=ready,
            status="ready" if ready else "degraded",
            checks=tuple(checks),
            reasons=reasons,
        )

    def _workspace_check(
        self,
        layout: RuntimeWorkspaceLayout | None,
    ) -> ReadinessCheck:
        if layout is None:
            return _degraded(
                ReadinessCheckName.WORKSPACE,
                ReadinessReason.WORKSPACE_NOT_CONFIGURED,
                "Configure BIJUX_CANON_RUNTIME_WORKING_ROOT and initialize it.",
            )
        try:
            validate_runtime_workspace(self._configuration, verify_model=False)
        except Exception:
            return _degraded(
                ReadinessCheckName.WORKSPACE,
                ReadinessReason.WORKSPACE_INVALID,
                "Initialize the workspace or restore one verified compatible backup.",
            )
        return _ready(ReadinessCheckName.WORKSPACE)

    @staticmethod
    def _schema_check(layout: RuntimeWorkspaceLayout | None) -> ReadinessCheck:
        if layout is None:
            return _degraded(
                ReadinessCheckName.SCHEMA,
                ReadinessReason.DATABASE_NOT_CONFIGURED,
                "Configure and initialize a Runtime workspace.",
            )
        try:
            store = DuckDBExecutionStore(layout.database_path, read_only=True)
            try:
                store.validate_schema()
            finally:
                store.close()
        except Exception:
            return _degraded(
                ReadinessCheckName.SCHEMA,
                ReadinessReason.SCHEMA_UNAVAILABLE,
                "Restore or migrate the initialized Runtime workspace.",
            )
        return _ready(ReadinessCheckName.SCHEMA)

    @staticmethod
    def _artifact_store_check(
        layout: RuntimeWorkspaceLayout | None,
    ) -> ReadinessCheck:
        if layout is None:
            return _degraded(
                ReadinessCheckName.ARTIFACT_STORE,
                ReadinessReason.ARTIFACT_STORE_NOT_CONFIGURED,
                "Configure and initialize a Runtime workspace.",
            )
        required = (
            layout.cas_root,
            layout.cas_root / "objects" / "sha256",
            layout.cas_root / "staging",
        )
        if any(not path.is_dir() or path.is_symlink() for path in required):
            return _degraded(
                ReadinessCheckName.ARTIFACT_STORE,
                ReadinessReason.ARTIFACT_STORE_UNAVAILABLE,
                "Restore the complete initialized Runtime workspace.",
            )
        return _ready(ReadinessCheckName.ARTIFACT_STORE)

    @staticmethod
    def _active_generation_check(
        layout: RuntimeWorkspaceLayout | None,
    ) -> tuple[object | None, ReadinessCheck]:
        if layout is None:
            return None, _degraded(
                ReadinessCheckName.ACTIVE_GENERATION,
                ReadinessReason.INDEX_NOT_CONFIGURED,
                "Configure and initialize a Runtime workspace.",
            )
        required = (
            layout.index_root,
            layout.index_root / "generations",
            layout.index_root / "registry.lock",
        )
        if any(not path.exists() or path.is_symlink() for path in required):
            return None, _degraded(
                ReadinessCheckName.ACTIVE_GENERATION,
                ReadinessReason.ACTIVE_GENERATION_UNAVAILABLE,
                "Build and activate a verified immutable index generation.",
            )
        try:
            report = IndexService(layout.index_root).verify()
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
                "Build and activate a verified immutable index generation.",
            )
        return report, _ready(ReadinessCheckName.ACTIVE_GENERATION)

    @staticmethod
    def _model_check(
        layout: RuntimeWorkspaceLayout | None,
        generation: object | None,
    ) -> ReadinessCheck:
        if layout is None:
            return _degraded(
                ReadinessCheckName.MODEL,
                ReadinessReason.MODEL_CONFIGURATION_UNAVAILABLE,
                "Configure a verified locked local embedding model.",
            )
        try:
            lock = load_model_lock(layout.model_lock_path)
            verify_materialized_model(layout.model_root, lock)
            if generation is not None and (
                getattr(generation, "model_lock_artifact_id", None) != lock.lock_id
                or getattr(generation, "dimension", None) != lock.profile.dimension
            ):
                raise ValueError("active generation and model lock differ")
        except Exception:
            return _degraded(
                ReadinessCheckName.MODEL,
                ReadinessReason.MODEL_CONFIGURATION_UNAVAILABLE,
                "Restore the locked local model used by the active index.",
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
                "Configure the selected provider credential reference or use offline mode.",
            )
        return _ready(ReadinessCheckName.PROVIDER)

    def _writable_state_check(
        self,
        layout: RuntimeWorkspaceLayout | None,
    ) -> ReadinessCheck:
        if layout is None:
            return _degraded(
                ReadinessCheckName.WRITABLE_STATE,
                ReadinessReason.STATE_NOT_WRITABLE,
                "Configure and initialize writable Runtime state.",
            )
        roots = {
            layout.root,
            layout.cas_root,
            layout.database_path.parent,
            layout.job_store_path.parent,
            layout.index_root,
            layout.operations_root,
            layout.vex_root,
            layout.locks_root,
            layout.staging_root,
            layout.temporary_root,
            layout.backup_root,
        }
        try:
            for root in sorted(roots):
                self._write_probe(root)
        except Exception:
            return _degraded(
                ReadinessCheckName.WRITABLE_STATE,
                ReadinessReason.STATE_NOT_WRITABLE,
                "Grant atomic write access to every initialized Runtime state root.",
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
    """Return whether an existing execution store has the exact current schema."""
    try:
        store = DuckDBExecutionStore(db_path, read_only=True)
        try:
            store.validate_schema()
        finally:
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
    "ReadinessCapability",
    "ReadinessCheck",
    "ReadinessCheckName",
    "ReadinessReason",
    "ReadinessReport",
    "RuntimeReadinessService",
    "runtime_liveness",
    "runtime_store_is_ready",
]
