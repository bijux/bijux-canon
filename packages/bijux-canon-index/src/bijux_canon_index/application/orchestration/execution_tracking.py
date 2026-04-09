# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Execution tracking helpers for application workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from bijux_canon_index.core.contracts.execution_contract import ExecutionContract
from bijux_canon_index.core.identity.fingerprints import determinism_fingerprint
from bijux_canon_index.core.identity.ids import fingerprint
from bijux_canon_index.core.types import ExecutionArtifact


@dataclass(frozen=True)
class ExecutionTrackingContext:
    """Represents execution tracking context."""

    ann_index_info: dict[str, object] | None
    vector_store_consistency: str | None
    vector_store_index_params: object | None
    backend_fingerprint: str
    determinism_fingerprint: str


def build_execution_tracking_context(
    *,
    artifact: ExecutionArtifact,
    backend: Any,
    stores: Any,
    vector_store_resolution: Any,
) -> ExecutionTrackingContext:
    """Build execution tracking context."""
    vector_store_meta = getattr(stores.vectors, "vector_store_metadata", None)
    vector_store_index_params = None
    vector_store_consistency = None
    if isinstance(vector_store_meta, dict):
        vector_store_index_params = vector_store_meta.get("index_params")
        vector_store_consistency = vector_store_meta.get("consistency")
    ann_index_info: dict[str, object] | None = None
    ann_runner = getattr(backend, "ann", None)
    if (
        artifact.execution_contract is ExecutionContract.NON_DETERMINISTIC
        and ann_runner is not None
        and hasattr(ann_runner, "index_info")
    ):
        ann_index_info = ann_runner.index_info(artifact.artifact_id)
    return ExecutionTrackingContext(
        ann_index_info=ann_index_info,
        vector_store_consistency=vector_store_consistency,
        vector_store_index_params=vector_store_index_params,
        backend_fingerprint=fingerprint(
            {
                "backend": getattr(backend, "name", "unknown"),
                "vector_store": {
                    "backend": vector_store_resolution.descriptor.name,
                    "version": vector_store_resolution.descriptor.version,
                    "consistency": vector_store_consistency,
                    "index_params": vector_store_index_params,
                },
            }
        ),
        determinism_fingerprint=determinism_fingerprint(
            artifact.vector_fingerprint,
            artifact.index_config_fingerprint,
            artifact.execution_plan.algorithm if artifact.execution_plan else None,
        ),
    )


__all__ = ["ExecutionTrackingContext", "build_execution_tracking_context"]
