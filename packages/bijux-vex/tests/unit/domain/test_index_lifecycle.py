# SPDX-License-Identifier: MIT
# SPDX-License-Identifier: MIT
from __future__ import annotations
from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.types import ExecutionArtifact
from bijux_vex.domain.execution_artifacts import lifecycle


def _artifact() -> ExecutionArtifact:
    return ExecutionArtifact(
        artifact_id="art",
        corpus_fingerprint="corp",
        vector_fingerprint="vec",
        metric="l2",
        scoring_version="v1",
        execution_contract=ExecutionContract.DETERMINISTIC,
        build_params=(("ef", "10"),),
    )


def test_index_lifecycle_states_and_fingerprint():
    art = _artifact()
    state = lifecycle.build(art)
    assert state.status is lifecycle.IndexState.READY
    building = lifecycle.begin_build(state)
    assert building.status is lifecycle.IndexState.BUILDING
    rebuilt = lifecycle.rebuild(building, art)
    assert rebuilt.status is lifecycle.IndexState.READY
    assert rebuilt.generation == 2
    invalid = lifecycle.invalidate(rebuilt)
    assert invalid.status is lifecycle.IndexState.INVALIDATED
