from __future__ import annotations

from bijux_canon_agent.pipeline.execution.iteration_transitions import (
    append_shard_result,
    apply_shard_failure,
    apply_validation_failure,
)
from bijux_canon_agent.pipeline.termination import ExecutionTerminationReason


def _pipeline_result() -> dict[str, object]:
    return {
        "audit_trail": [],
        "revision_history": [],
        "execution_path": [],
        "warnings": [],
        "final_status": {
            "success": True,
            "termination_reason": ExecutionTerminationReason.COMPLETED,
        },
    }


def test_append_shard_result_merges_lists() -> None:
    pipeline_result = _pipeline_result()

    append_shard_result(
        pipeline_result,
        {
            "audit_trail": [{"stage": "plan"}],
            "revision_history": [{"revision": 1}],
            "execution_path": [{"node": "planner"}],
            "warnings": ["low confidence"],
        },
    )

    assert pipeline_result["audit_trail"] == [{"stage": "plan"}]
    assert pipeline_result["revision_history"] == [{"revision": 1}]
    assert pipeline_result["execution_path"] == [{"node": "planner"}]
    assert pipeline_result["warnings"] == ["low confidence"]


def test_apply_shard_failure_sets_failure_status() -> None:
    pipeline_result = _pipeline_result()

    updated = apply_shard_failure(
        pipeline_result,
        {
            "error": "reader failed",
            "final_status": {
                "stages_processed": ["read"],
                "iterations": 2,
            },
        },
    )

    assert updated["final_status"] == {
        "success": False,
        "error": "reader failed",
        "stages_processed": ["read"],
        "iterations": 2,
        "termination_reason": ExecutionTerminationReason.FAILURE,
        "converged": False,
        "convergence_reason": None,
        "convergence_iterations": 0,
    }


def test_apply_validation_failure_sets_terminal_error() -> None:
    pipeline_result = _pipeline_result()

    updated = apply_validation_failure(
        pipeline_result,
        {"issues": ["missing evidence"]},
    )

    assert updated["final_status"] == {
        "success": False,
        "termination_reason": ExecutionTerminationReason.FAILURE,
        "error": "Final result does not meet task goal: ['missing evidence']",
    }
