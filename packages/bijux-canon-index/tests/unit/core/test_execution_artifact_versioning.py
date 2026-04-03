# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
import pytest

from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.errors import InvariantError
from bijux_vex.core.types import ExecutionArtifact


def test_default_schema_version_is_v1():
    art = ExecutionArtifact(
        artifact_id="art-1",
        corpus_fingerprint="corp",
        vector_fingerprint="vec",
        metric="l2",
        scoring_version="v1",
        execution_contract=ExecutionContract.DETERMINISTIC,
    )
    assert art.schema_version == "v1"


def test_future_schema_version_rejected():
    with pytest.raises(InvariantError):
        ExecutionArtifact(
            artifact_id="art-1",
            corpus_fingerprint="corp",
            vector_fingerprint="vec",
            metric="l2",
            scoring_version="v1",
            schema_version="v2",
            execution_contract=ExecutionContract.DETERMINISTIC,
        )


def test_old_execution_artifact_version_rejected():
    with pytest.raises(InvariantError):
        ExecutionArtifact(
            artifact_id="art-legacy",
            corpus_fingerprint="corp",
            vector_fingerprint="vec",
            metric="l2",
            scoring_version="v1",
            execution_contract=ExecutionContract.DETERMINISTIC,
            execution_artifact_version="0.9",
        )
