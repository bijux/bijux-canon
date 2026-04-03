"""Invariant: pipeline module depth stays shallow."""

from __future__ import annotations

from pathlib import Path


def test_pipeline_module_depth() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    pipeline_root = repo_root / "src" / "bijux_agent" / "pipeline"
    violations: list[str] = []
    for path in pipeline_root.rglob("*.py"):
        if not path.is_file():
            continue
        relative = path.relative_to(pipeline_root)
        parts = relative.parts
        if len(parts) > 2:
            violations.append(str(relative))
    assert not violations, (
        "Pipeline modules must live at pipeline/<layer>/<module>.py: "
        f"{sorted(violations)}"
    )
