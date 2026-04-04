from __future__ import annotations

from bijux_canon_agent.agents.stage_runner.execution_flow import (
    add_stage_warning,
    build_stage_inputs,
    initialize_stage_runner_result,
    record_completion,
    record_stage_success,
)


def test_build_stage_inputs_merges_dependency_outputs() -> None:
    result = initialize_stage_runner_result()
    result["stages"]["reader"] = {"text": "hello"}

    inputs = build_stage_inputs(
        {"file_path": "note.txt"},
        result,
        ["reader"],
    )

    assert inputs == {"text": "hello", "file_path": "note.txt"}


def test_record_stage_success_tracks_audit_and_status() -> None:
    result = initialize_stage_runner_result()

    record_stage_success(
        result,
        stage_name="reader",
        stage_output={"text": "hello"},
        stage_duration=0.42,
    )

    assert result["final_status"]["stages_processed"] == ["reader"]
    assert result["audit_trail"][0]["stage_name"] == "reader"


def test_record_completion_and_warning_update_result() -> None:
    result = initialize_stage_runner_result()
    add_stage_warning(result, "stage skipped")
    record_completion(result, 1.5)

    assert result["warnings"] == ["stage skipped"]
    assert result["audit_trail"][-1]["stages_processed"] == []
