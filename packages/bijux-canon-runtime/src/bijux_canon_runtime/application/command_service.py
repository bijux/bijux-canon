# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Application services invoked by runtime command transports."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
import os
from pathlib import Path

from bijux_canon_runtime.application.execute_flow import ExecutionConfig, FlowRunResult
from bijux_canon_runtime.application.planner import ExecutionPlanner
from bijux_canon_runtime.application.replay_store import replay_with_store
from bijux_canon_runtime.application.runtime_configuration import (
    resolve_runtime_configuration,
)
from bijux_canon_runtime.model.execution.run_mode import RunMode
from bijux_canon_runtime.model.flows.manifest import FlowManifest
from bijux_canon_runtime.model.verification.verification import VerificationPolicy
from bijux_canon_runtime.observability.storage.execution_store import (
    DuckDBExecutionReadStore,
    DuckDBExecutionWriteStore,
)
from bijux_canon_runtime.ontology.ids import RunID, TenantID


def prepare_execution(
    *,
    manifest: FlowManifest,
    command: str,
    db_path: Path | None,
    strict_determinism: bool,
    policy: VerificationPolicy | None,
    environment: Mapping[str, str] | None = None,
) -> tuple[FlowManifest, ExecutionConfig]:
    """Construct explicit execution adapters for a parsed manifest."""
    explicit: dict[str, object] = {}
    if db_path is not None:
        explicit["database_path"] = db_path
    if strict_determinism:
        explicit["strict_determinism"] = True
    settings = resolve_runtime_configuration(
        environment=os.environ if environment is None else environment,
        explicit=explicit,
    )
    config = ExecutionConfig.from_command(command).for_manifest(manifest)
    config = replace(
        config,
        strict_determinism=settings.strict_determinism,
        budget=settings.resource_budget,
        runtime_configuration=settings,
    )
    if settings.database_path is not None:
        config = replace(
            config,
            execution_store=DuckDBExecutionWriteStore(settings.database_path),
        )
    if policy is not None:
        config = replace(config, verification_policy=policy)
    return manifest, config


def replay_persisted_run(
    *,
    manifest: FlowManifest,
    policy: VerificationPolicy,
    db_path: Path,
    run_id: str,
    tenant_id: str,
    strict_determinism: bool,
    environment: Mapping[str, str] | None = None,
) -> tuple[dict[str, object], FlowRunResult]:
    """Replay one persisted run using application-owned storage adapters."""
    settings = resolve_runtime_configuration(
        environment=os.environ if environment is None else environment,
        explicit={
            "database_path": db_path,
            **({"strict_determinism": True} if strict_determinism else {}),
        },
    )
    resolved_flow = ExecutionPlanner().resolve(manifest)
    if settings.database_path is None:
        raise ValueError("database_path is required for replay")
    read_store = DuckDBExecutionReadStore(settings.database_path)
    write_store = DuckDBExecutionWriteStore(settings.database_path)
    config = ExecutionConfig(
        mode=RunMode.LIVE,
        determinism_level=manifest.determinism_level,
        execution_store=write_store,
        execution_read_store=read_store,
        verification_policy=policy,
        strict_determinism=settings.strict_determinism,
        budget=settings.resource_budget,
        runtime_configuration=settings,
    )
    return replay_with_store(
        store=read_store,
        run_id=RunID(run_id),
        tenant_id=TenantID(tenant_id),
        resolved_flow=resolved_flow,
        config=config,
    )


__all__ = ["prepare_execution", "replay_persisted_run"]
