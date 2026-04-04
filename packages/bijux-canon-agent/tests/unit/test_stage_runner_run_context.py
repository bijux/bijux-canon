from __future__ import annotations

from pathlib import Path

from bijux_canon_agent.agents.stage_runner.run_context import (
    apply_stage_output_to_context,
    stage_skip_warning,
    validate_stage_runner_context,
)


def test_validate_stage_runner_context_requires_file_path(tmp_path: Path) -> None:
    assert (
        validate_stage_runner_context({})
        == "Input context must provide 'file_path' for stage execution"
    )
    assert (
        validate_stage_runner_context({"file_path": str(tmp_path / "input.txt")})
        is None
    )


def test_stage_skip_warning_uses_stage_condition() -> None:
    warning = stage_skip_warning(
        {"name": "summarize", "condition": lambda context: context.get("ready", False)},
        {"ready": False},
    )

    assert warning == "Stage 'summarize' skipped due to unmet condition"
    assert (
        stage_skip_warning(
            {"name": "summarize", "condition": lambda context: True},
            {"ready": True},
        )
        is None
    )


def test_apply_stage_output_to_context_uses_explicit_output_key(tmp_path: Path) -> None:
    context = {"file_path": str(tmp_path / "input.txt")}

    apply_stage_output_to_context(
        context,
        stage={"name": "summarize", "output_key": "summary"},
        stage_output={"text": "done"},
    )

    assert context["summary"] == {"text": "done"}
