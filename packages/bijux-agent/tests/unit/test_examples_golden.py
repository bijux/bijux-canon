from __future__ import annotations

import json
from pathlib import Path

from bijux_agent.cli.helpers import load_trace
from bijux_agent.pipeline.results.outcome import PipelineResult


def test_examples_golden_output_matches_trace() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    root = repo_root / "examples" / "golden"
    final_result_path = root / "result" / "final_result.json"
    trace_path = root / "trace" / "run_trace.json"

    assert final_result_path.exists(), (
        "examples/golden/result/final_result.json missing"
    )
    assert trace_path.exists(), "examples/golden/trace/run_trace.json missing"

    final_payload = json.loads(final_result_path.read_text(encoding="utf-8"))
    trace = load_trace(trace_path)
    reconstructed = PipelineResult.from_trace(trace)

    assert final_payload["verdict"] == reconstructed.decision.value
    assert abs(final_payload["confidence"] - reconstructed.confidence) < 1e-6
    assert final_payload["epistemic_status"] == reconstructed.epistemic_verdict.value
    expected_stop_reason = (
        final_payload["stop_reason"]
        if final_payload["stop_reason"] is not None
        else None
    )
    actual_stop_reason = (
        reconstructed.stop_reason.value if reconstructed.stop_reason else None
    )
    assert expected_stop_reason == actual_stop_reason
    assert final_payload["trace_path"] == "trace/run_trace.json"
    assert final_payload["runtime_version"] == "golden-runtime"
    assert (root / final_payload["trace_path"]).exists()
