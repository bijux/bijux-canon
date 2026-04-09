# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""
Execution artifact migration stubs.

We keep a forward-only policy: artifacts must be migrated explicitly
if their version lags behind the engine's supported version.
"""

from __future__ import annotations

from bijux_canon_index.core.errors import InvariantError
from bijux_canon_index.core.types import ExecutionArtifact

SUPPORTED_VERSION = "1.0"


def migrate_execution_artifact(
    artifact: ExecutionArtifact, target_version: str = SUPPORTED_VERSION
) -> ExecutionArtifact:
    """Handle migrate execution artifact."""
    if artifact.execution_artifact_version == target_version:
        return artifact
    raise InvariantError(
        message=(
            "Migration path for execution artifacts is not yet implemented; "
            f"have {artifact.execution_artifact_version}, want {target_version}"
        )
    )


__all__ = ["SUPPORTED_VERSION", "migrate_execution_artifact"]
