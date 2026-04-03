# SPDX-License-Identifier: MIT
# SPDX-License-Identifier: MIT
from __future__ import annotations
import pytest

from bijux_vex.core.contracts.invariants import (
    assert_invariants,
    invariant_execution_contract_match,
    invariant_provenance_required,
    invariant_randomness_required,
)
from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.execution_intent import ExecutionIntent
from bijux_vex.core.execution_mode import ExecutionMode
from bijux_vex.core.errors import InvariantError
from bijux_vex.core.types import ExecutionArtifact, ExecutionBudget, ExecutionRequest


@pytest.fixture()
def artifact():
    return ExecutionArtifact(
        artifact_id="a",
        corpus_fingerprint="c",
        vector_fingerprint="v",
        metric="l2",
        scoring_version="v1",
        execution_contract=ExecutionContract.DETERMINISTIC,
    )


@pytest.fixture()
def request_det():
    return ExecutionRequest(
        request_id="r",
        text=None,
        vector=(0.1,),
        top_k=1,
        execution_contract=ExecutionContract.DETERMINISTIC,
        execution_intent=ExecutionIntent.EXACT_VALIDATION,
        execution_mode=ExecutionMode.STRICT,
    )


def test_execution_contract_invariant_passes(artifact, request_det):
    inv = invariant_execution_contract_match(artifact, request_det)
    assert inv.predicate() is True
    assert_invariants([inv])


def test_execution_contract_invariant_fails(artifact, request_det):
    nd_req = ExecutionRequest(
        request_id="r2",
        text=None,
        vector=(0.1,),
        top_k=1,
        execution_contract=ExecutionContract.NON_DETERMINISTIC,
        execution_intent=ExecutionIntent.EXPLORATORY_SEARCH,
        execution_mode=ExecutionMode.BOUNDED,
        execution_budget=ExecutionBudget(max_ann_probes=1),
    )
    inv = invariant_execution_contract_match(artifact, nd_req)
    with pytest.raises(AssertionError):
        assert_invariants([inv])


def test_randomness_invariant_requires_budget():
    with pytest.raises(InvariantError):
        ExecutionRequest(
            request_id="r3",
            text=None,
            vector=(0.1,),
            top_k=1,
            execution_contract=ExecutionContract.NON_DETERMINISTIC,
            execution_intent=ExecutionIntent.EXPLORATORY_SEARCH,
            execution_mode=ExecutionMode.BOUNDED,
        )


def test_provenance_invariant_placeholder(artifact):
    inv = invariant_provenance_required(artifact)
    assert inv.invariant_id == "INV-040"
    assert_invariants([inv])
