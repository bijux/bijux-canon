# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Application services invoked by runtime command transports."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from bijux_canon_runtime.application.execute_flow import ExecutionConfig, FlowRunResult
from bijux_canon_runtime.application.planner import ExecutionPlanner
from bijux_canon_runtime.application.replay_store import replay_with_store
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
) -> tuple[FlowManifest, ExecutionConfig]:
    """Construct explicit execution adapters for a parsed manifest."""
    config = ExecutionConfig.from_command(command).for_manifest(manifest)
    if db_path is not None:
        config = ExecutionConfig(
            mode=config.mode,
            determinism_level=manifest.determinism_level,
            execution_store=DuckDBExecutionWriteStore(db_path),
        )
    if strict_determinism:
        config = replace(config, strict_determinism=True)
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
) -> tuple[dict[str, object], FlowRunResult]:
    """Replay one persisted run using application-owned storage adapters."""
    resolved_flow = ExecutionPlanner().resolve(manifest)
    read_store = DuckDBExecutionReadStore(db_path)
    write_store = DuckDBExecutionWriteStore(db_path)
    config = ExecutionConfig(
        mode=RunMode.LIVE,
        determinism_level=manifest.determinism_level,
        execution_store=write_store,
        execution_read_store=read_store,
        verification_policy=policy,
        strict_determinism=strict_determinism,
    )
    return replay_with_store(
        store=read_store,
        run_id=RunID(run_id),
        tenant_id=TenantID(tenant_id),
        resolved_flow=resolved_flow,
        config=config,
    )


__all__ = ["prepare_execution", "replay_persisted_run"]
