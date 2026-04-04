from __future__ import annotations

from bijux_canon_agent.pipeline.results.shard_merging import (
    collect_stage_outputs,
    initialize_merged_final_status,
    merge_stage_outputs,
    propagate_shard_status,
    update_critique_status,
)
from bijux_canon_agent.pipeline.termination import ExecutionTerminationReason


def test_collect_stage_outputs_separates_errors() -> None:
    outputs, errors = collect_stage_outputs(
        "summarization",
        [
            {
                "stages": {"summarization": {"summary": "ok"}},
                "final_status": {"iterations": 1},
            },
            {
                "stages": {"summarization": {"error": "boom"}},
                "final_status": {"iterations": 1},
            },
        ],
    )

    assert outputs == [{"summary": "ok"}]
    assert errors == ["Shard failed in stage summarization: boom"]


def test_merge_stage_outputs_adds_audit_for_non_summary_stage() -> None:
    merged = merge_stage_outputs("critique", [{"score": 0.9}])

    assert merged["score"] == 0.9
    assert merged["audit"]["shards_merged"] == 1


def test_update_critique_status_and_propagate_shard_status() -> None:
    final_status = initialize_merged_final_status()
    shard_results = [
        {
            "stages": {},
            "final_status": {
                "iterations": 2,
                "converged": True,
                "convergence_reason": "stable",
                "termination_reason": (ExecutionTerminationReason.RESOURCE_EXHAUSTION),
            },
        }
    ]

    update_critique_status(
        final_status,
        {"critique_status": "ok", "score": 0.95},
        quality_threshold=0.8,
        has_errors=False,
        shard_results=shard_results,
    )
    propagate_shard_status(final_status, shard_results)

    assert final_status["success"] is True
    assert final_status["iterations"] == 2
    assert final_status["converged"] is True
    assert (
        final_status["termination_reason"]
        == ExecutionTerminationReason.RESOURCE_EXHAUSTION
    )
