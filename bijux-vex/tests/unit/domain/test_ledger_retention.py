# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.errors import InvariantError
from bijux_vex.core.execution_result import ExecutionCost, ExecutionResult
from bijux_vex.core.runtime.execution_plan import ExecutionPlan
from bijux_vex.core.types import Result
from bijux_vex.infra.adapters.memory.backend import (
    MemoryExecutionLedger,
    memory_backend,
)


def _fake_result(execution_id: str) -> ExecutionResult:
    plan = ExecutionPlan(
        algorithm="exact",
        contract=ExecutionContract.DETERMINISTIC,
        k=1,
        scoring_fn="l2",
        randomness_sources=(),
        reproducibility_bounds="bit-identical",
        steps=("plan", "execute"),
    )
    return ExecutionResult(
        execution_id=execution_id,
        signature="sig",
        artifact_id="art",
        plan=plan,
        results=tuple(
            Result(
                request_id=execution_id,
                document_id="doc",
                chunk_id="chunk",
                vector_id="vec",
                artifact_id="art",
                score=1.0,
                rank=1,
            )
            for _ in ()
        ),
        cost=ExecutionCost(
            vector_reads=0,
            distance_computations=0,
            graph_hops=0,
            wall_time_estimate_ms=0.0,
        ),
    )


def test_memory_ledger_enforces_result_retention_limit():
    fixture = memory_backend()
    ledger: MemoryExecutionLedger = fixture.stores.ledger  # type: ignore[assignment]
    original_limit = ledger.MAX_RESULTS
    ledger.MAX_RESULTS = 2
    try:
        with fixture.tx_factory() as tx:
            ledger.put_execution_result(tx, _fake_result("r1"))
            ledger.put_execution_result(tx, _fake_result("r2"))
            tx.commit()
        with fixture.tx_factory() as tx:
            try:
                ledger.put_execution_result(tx, _fake_result("r3"))
                assert False, "expected retention failure"
            except InvariantError:
                pass
    finally:
        ledger.MAX_RESULTS = original_limit
