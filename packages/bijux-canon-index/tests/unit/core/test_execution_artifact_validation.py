# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from typing import Any, cast

from bijux_canon_index.core.contracts.execution_contract import ExecutionContract
from bijux_canon_index.core.errors import InvariantError
from bijux_canon_index.core.types import ExecutionArtifact
import pytest


def test_execution_artifact_validates_required_fields() -> None:
    with pytest.raises(InvariantError):
        ExecutionArtifact(
            artifact_id="art",
            corpus_fingerprint="",
            vector_fingerprint="vec",
            metric="l2",
            scoring_version="v1",
            execution_contract=ExecutionContract.DETERMINISTIC,
        )
    with pytest.raises(InvariantError):
        ExecutionArtifact(
            artifact_id="art",
            corpus_fingerprint="corp",
            vector_fingerprint="",
            metric="l2",
            scoring_version="v1",
            execution_contract=ExecutionContract.DETERMINISTIC,
        )
    with pytest.raises(InvariantError):
        ExecutionArtifact(
            artifact_id="art",
            corpus_fingerprint="corp",
            vector_fingerprint="vec",
            metric="",
            scoring_version="",
            execution_contract=ExecutionContract.DETERMINISTIC,
        )


def test_execution_artifact_forbids_unknown_fields() -> None:
    with pytest.raises(TypeError):
        cast(Any, ExecutionArtifact)(
            artifact_id="art",
            corpus_fingerprint="corp",
            vector_fingerprint="vec",
            metric="l2",
            scoring_version="v1",
            execution_contract=ExecutionContract.DETERMINISTIC,
            extra="nope",
        )


def test_build_params_are_canonicalized() -> None:
    artifact = ExecutionArtifact(
        artifact_id="art",
        corpus_fingerprint="corp",
        vector_fingerprint="vec",
        metric="l2",
        scoring_version="v1",
        build_params=(("k1", "v1"), ("k2", "v2")),
        execution_contract=ExecutionContract.DETERMINISTIC,
    )
    assert artifact.build_params == (("k1", "v1"), ("k2", "v2"))


def test_replayable_matches_contract() -> None:
    deterministic = ExecutionArtifact(
        artifact_id="art",
        corpus_fingerprint="corp",
        vector_fingerprint="vec",
        metric="l2",
        scoring_version="v1",
        execution_contract=ExecutionContract.DETERMINISTIC,
    )
    assert deterministic.replayable is True
    ann = ExecutionArtifact(
        artifact_id="art-ann",
        corpus_fingerprint="corp",
        vector_fingerprint="vec",
        metric="l2",
        scoring_version="v1",
        execution_contract=ExecutionContract.NON_DETERMINISTIC,
    )
    assert ann.replayable is False


def test_artifact_growth_limits() -> None:
    oversized_params = tuple((str(i), str(i)) for i in range(300))
    with pytest.raises(InvariantError):
        ExecutionArtifact(
            artifact_id="art-big",
            corpus_fingerprint="corp",
            vector_fingerprint="vec",
            metric="l2",
            scoring_version="v1",
            execution_contract=ExecutionContract.DETERMINISTIC,
            build_params=oversized_params,
        )
