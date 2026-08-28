# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Secret-safe discovery of the effective installed Runtime product."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from enum import Enum
import os
from typing import cast, get_args

from bijux_canon_index.application import IndexService
from bijux_canon_index.application.model_lifecycle import (
    MODEL_RECORD_NAME,
    ModelLifecycleError,
    load_model_record,
)
from bijux_canon_index.infra.embeddings.model_cache import (
    load_model_lock,
    verify_materialized_model,
)
from bijux_canon_ingest.domain.source_admission import SourceFormat
from bijux_canon_runtime.application.operations import ApplicationOperation
from bijux_canon_runtime.application.readiness import (
    ReadinessCapability,
    ReadinessReport,
    RuntimeReadinessService,
)
from bijux_canon_runtime.application.runtime_configuration import (
    RuntimeConfiguration,
    resolve_runtime_configuration,
)
from bijux_canon_runtime.application.workspace_initialization import (
    validate_runtime_workspace,
)
from bijux_canon_runtime.core.package_versions import distribution_version
from bijux_canon_runtime.model.execution.request_plan import (
    SUPPORTED_LOCAL_REASON_PROVIDERS,
)


@dataclass(frozen=True, slots=True)
class InstalledDistributionDiscovery:
    """One exact installed canonical distribution version."""

    name: str
    version: str


@dataclass(frozen=True, slots=True)
class ParserDiscovery:
    """One installed source format and its admission disposition."""

    format_id: str
    disposition: str


@dataclass(frozen=True, slots=True)
class ProviderDiscovery:
    """One provider identifier accepted by the installed reasoning adapter."""

    provider_id: str
    provider_kind: str
    credential_required: bool


@dataclass(frozen=True, slots=True)
class WorkspaceDiscovery:
    """Safe identity of the configured persistent workspace."""

    status: str
    workspace_id: str | None
    workspace_version: int | None
    layout_identity_sha256: str | None


@dataclass(frozen=True, slots=True)
class ModelDiscovery:
    """Safe identity of the verified configured embedding model."""

    status: str
    model_lock_artifact_id: str | None
    profile_id: str | None
    provider_kind: str | None
    model_id: str | None
    revision: str | None
    dimension: int | None
    validation_record_id: str | None
    artifact_set_digest: str | None
    license_pointer: str | None
    compatibility_status: str | None
    validation_result: str | None
    offline_reuse: bool


@dataclass(frozen=True, slots=True)
class IndexDiscovery:
    """Safe identity of the active verified immutable index generation."""

    status: str
    generation_id: str | None
    snapshot_artifact_id: str | None
    model_lock_artifact_id: str | None
    chunk_set_sha256: str | None
    chunk_count: int | None
    dimension: int | None


@dataclass(frozen=True, slots=True)
class RuntimeCapabilityDiscovery:
    """One transport-neutral, secret-safe product discovery report."""

    schema_version: str
    configuration: dict[str, object]
    provider_credential_available: bool
    workspace: WorkspaceDiscovery
    model: ModelDiscovery
    index: IndexDiscovery
    installed_distributions: tuple[InstalledDistributionDiscovery, ...]
    operations: tuple[str, ...]
    parsers: tuple[ParserDiscovery, ...]
    providers: tuple[ProviderDiscovery, ...]
    readiness: tuple[ReadinessReport, ...]

    def record(self) -> dict[str, object]:
        """Return the canonical JSON-compatible discovery representation."""
        return cast(dict[str, object], _json_value(asdict(self)))


class RuntimeCapabilityDiscoveryService:
    """Inspect one already resolved configuration without exposing credentials."""

    def __init__(
        self,
        configuration: RuntimeConfiguration,
        *,
        environment: Mapping[str, str] | None = None,
    ) -> None:
        self._configuration = configuration
        self._environment = dict(os.environ if environment is None else environment)

    def inspect(self) -> RuntimeCapabilityDiscovery:
        """Return identities, installed support, and readiness for every operation."""
        credential = self._configuration.provider_api_key
        readiness_service = RuntimeReadinessService(
            self._configuration,
            environment=self._environment,
        )
        return RuntimeCapabilityDiscovery(
            schema_version="bijux.runtime.capability-discovery.v1",
            configuration=self._configuration.redacted_record(),
            provider_credential_available=(
                False
                if credential is None
                else credential.is_available(self._environment)
            ),
            workspace=self._workspace(),
            model=self._model(),
            index=self._index(),
            installed_distributions=_installed_distributions(),
            operations=tuple(operation.value for operation in ApplicationOperation),
            parsers=_parser_discovery(),
            providers=tuple(
                ProviderDiscovery(
                    provider_id=provider_id,
                    provider_kind="local",
                    credential_required=False,
                )
                for provider_id in SUPPORTED_LOCAL_REASON_PROVIDERS
            ),
            readiness=tuple(
                readiness_service.evaluate(capability)
                for capability in ReadinessCapability
            ),
        )

    def _workspace(self) -> WorkspaceDiscovery:
        if self._configuration.workspace_layout is None:
            return WorkspaceDiscovery("not_configured", None, None, None)
        try:
            result = validate_runtime_workspace(
                self._configuration,
                verify_model=False,
            )
        except Exception:
            return WorkspaceDiscovery("unavailable", None, None, None)
        return WorkspaceDiscovery(
            status="initialized",
            workspace_id=result.workspace_id,
            workspace_version=result.workspace_version,
            layout_identity_sha256=result.layout_identity_sha256,
        )

    def _model(self) -> ModelDiscovery:
        layout = self._configuration.workspace_layout
        if layout is None:
            return _empty_model("not_configured")
        try:
            lock = load_model_lock(layout.model_lock_path)
            verify_materialized_model(layout.model_root, lock)
        except Exception:
            return _empty_model("unavailable")
        validation_record_id: str | None = None
        artifact_set_digest: str | None = None
        license_pointer: str | None = None
        compatibility_status: str | None = None
        validation_result: str | None = "not_recorded"
        offline_reuse = False
        record_path = layout.model_root / MODEL_RECORD_NAME
        if record_path.exists():
            try:
                record = load_model_record(record_path)
            except ModelLifecycleError:
                validation_result = "record_invalid"
            else:
                if record.model_lock_artifact_id != lock.lock_id:
                    validation_result = "record_mismatch"
                else:
                    validation_record_id = record.record_id
                    artifact_set_digest = record.artifact_set_digest
                    license_pointer = record.license_pointer
                    compatibility_status = record.compatibility.status
                    validation_result = record.validation_result
                    offline_reuse = record.offline_reuse
        return ModelDiscovery(
            status="verified",
            model_lock_artifact_id=lock.lock_id,
            profile_id=lock.profile.profile_id,
            provider_kind=lock.profile.provider_kind,
            model_id=lock.profile.model_id,
            revision=lock.profile.revision,
            dimension=lock.profile.dimension,
            validation_record_id=validation_record_id,
            artifact_set_digest=artifact_set_digest,
            license_pointer=license_pointer,
            compatibility_status=compatibility_status,
            validation_result=validation_result,
            offline_reuse=offline_reuse,
        )

    def _index(self) -> IndexDiscovery:
        layout = self._configuration.workspace_layout
        if layout is None:
            return _empty_index("not_configured")
        if (
            not layout.index_root.is_dir()
            or layout.index_root.is_symlink()
            or not layout.active_generation_path.is_file()
            or layout.active_generation_path.is_symlink()
        ):
            return _empty_index("unavailable")
        try:
            report = IndexService(layout.index_root).verify()
            if not report.activation.active:
                raise ValueError("verified generation is not active")
        except Exception:
            return _empty_index("unavailable")
        return IndexDiscovery(
            status="active",
            generation_id=report.generation_id,
            snapshot_artifact_id=report.snapshot_artifact_id,
            model_lock_artifact_id=report.model_lock_artifact_id,
            chunk_set_sha256=report.chunk_set_sha256,
            chunk_count=report.chunk_count,
            dimension=report.dimension,
        )


def _empty_model(status: str) -> ModelDiscovery:
    return ModelDiscovery(
        status,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        False,
    )


def _json_value(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_json_value(item) for item in value]
    return value


def _empty_index(status: str) -> IndexDiscovery:
    return IndexDiscovery(status, None, None, None, None, None, None)


def _installed_distributions() -> tuple[InstalledDistributionDiscovery, ...]:
    names = (
        "bijux-canon-agent",
        "bijux-canon-index",
        "bijux-canon-ingest",
        "bijux-canon-reason",
        "bijux-canon-runtime",
    )
    return tuple(
        InstalledDistributionDiscovery(name, distribution_version(name))
        for name in names
    )


def _parser_discovery() -> tuple[ParserDiscovery, ...]:
    return tuple(
        ParserDiscovery(
            format_id=format_id,
            disposition=(
                "typed_refusal" if format_id == "ocr-required" else "supported"
            ),
        )
        for format_id in get_args(SourceFormat)
    )


def discover_runtime_capabilities(
    configuration: RuntimeConfiguration | None = None,
    *,
    environment: Mapping[str, str] | None = None,
) -> RuntimeCapabilityDiscovery:
    """Discover the effective installed product through the public Python surface."""
    selected_environment = os.environ if environment is None else environment
    effective = configuration or resolve_runtime_configuration(
        environment=selected_environment,
    )
    return RuntimeCapabilityDiscoveryService(
        effective,
        environment=selected_environment,
    ).inspect()


__all__ = [
    "IndexDiscovery",
    "InstalledDistributionDiscovery",
    "ModelDiscovery",
    "ParserDiscovery",
    "ProviderDiscovery",
    "RuntimeCapabilityDiscovery",
    "RuntimeCapabilityDiscoveryService",
    "WorkspaceDiscovery",
    "discover_runtime_capabilities",
]
