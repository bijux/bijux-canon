# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from bijux_canon_index.core.contracts.execution_contract import ExecutionContract
from bijux_canon_index.core.errors import InvariantError
from bijux_canon_index.core.invariants import (
    ALLOWED_METRICS,
    validate_execution_artifact,
)
from bijux_canon_index.core.types import ExecutionArtifact
import pytest


def test_validate_execution_artifact_happy_path():
    artifact = ExecutionArtifact(
        artifact_id="art-1",
        corpus_fingerprint="corp-fp",
        vector_fingerprint="vec-fp",
        metric=next(iter(ALLOWED_METRICS)),
        scoring_version="v1",
        build_params=(("param", "value"),),
        execution_contract=ExecutionContract.DETERMINISTIC,
    )
    validate_execution_artifact(artifact)


@pytest.mark.parametrize("field", ["corpus_fingerprint", "vector_fingerprint"])
def test_validate_execution_artifact_empty_fingerprints(field: str):
    kwargs = dict(
        artifact_id="art-1",
        corpus_fingerprint="corp-fp",
        vector_fingerprint="vec-fp",
        metric=next(iter(ALLOWED_METRICS)),
        scoring_version="v1",
        build_params=(),
        execution_contract=ExecutionContract.DETERMINISTIC,
    )
    kwargs[field] = ""
    with pytest.raises(InvariantError):
        ExecutionArtifact(**kwargs)


def test_validate_execution_artifact_invalid_metric():
    with pytest.raises(InvariantError):
        ExecutionArtifact(
            artifact_id="art-1",
            corpus_fingerprint="corp-fp",
            vector_fingerprint="vec-fp",
            metric="invalid",
            scoring_version="v1",
            build_params=(),
            execution_contract=ExecutionContract.DETERMINISTIC,
        )
