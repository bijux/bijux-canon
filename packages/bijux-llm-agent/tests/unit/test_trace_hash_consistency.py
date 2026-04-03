"""Ensure trace serialization stays stable across identical runs."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC
from datetime import datetime as real_datetime
import hashlib
import json
from pathlib import Path
from typing import Any
import uuid

from tests.utils.trace_helpers import default_model_metadata

from bijux_agent.cli.helpers import build_trace_from_result
from bijux_agent.enums import DecisionOutcome
from bijux_agent.pipeline.termination import ExecutionTerminationReason


class FixedDatetime(real_datetime):  # reuse as base for patched datetime
    """Stub datetime that always returns the same timestamp."""

    @classmethod
    def now(cls, tz=None):
        return real_datetime(2024, 1, 1, tzinfo=UTC)


def _pipeline_result_template() -> dict[str, Any]:
    return {
        "final_status": {
            "success": True,
            "score": 0.93,
            "stages_processed": ["summarization"],
            "termination_reason": ExecutionTerminationReason.COMPLETED,
            "converged": False,
            "convergence_reason": None,
            "convergence_iterations": 0,
        },
        "result": {"text": "stable payload"},
        "stages": {"summarization": {"summary": "text"}},
    }


def _trace_hash(trace_dict: dict[str, Any]) -> str:
    serialized = json.dumps(trace_dict, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def test_trace_reproducible_hash(monkeypatch, tmp_path: Path) -> None:
    """Identical pipeline outputs must yield identical trace hashes."""

    monkeypatch.setattr("bijux_agent.cli.helpers.datetime", FixedDatetime)
    monkeypatch.setattr(
        "bijux_agent.cli.helpers.uuid.uuid4",
        lambda: uuid.UUID(int=0),
    )

    def make_trace(path: Path) -> tuple[dict[str, Any], str]:
        pipeline_result = _pipeline_result_template()
        trace_path, trace = build_trace_from_result(
            pipeline_result=pipeline_result,
            file_path="stable.txt",
            task_goal="ensure trace",
            config={
                "pipeline": {"enabled": True},
                "model_metadata": asdict(default_model_metadata()),
            },
            verdict=DecisionOutcome.PASS,
            confidence=float(pipeline_result["final_status"]["score"]),
            trace_dir=path,
            convergence_hash="stable-hash",
            convergence_reason="stability",
        )
        trace_dict = trace.to_dict()
        return trace_dict, _trace_hash(trace_dict)

    trace_dir1 = tmp_path / "trace-one"
    trace_dir2 = tmp_path / "trace-two"
    dict_one, hash_one = make_trace(trace_dir1)
    dict_two, hash_two = make_trace(trace_dir2)

    if hash_one != hash_two:
        mismatches = [
            key
            for key in sorted(set(dict_one) | set(dict_two))
            if dict_one.get(key) != dict_two.get(key)
        ]
        raise AssertionError(
            f"Trace hashes diverged ({hash_one} != {hash_two}); "
            f"differing keys: {mismatches}"
        )

    assert hash_one == hash_two


def test_trace_runtime_version_changes_with_git(monkeypatch, tmp_path: Path) -> None:
    """Trace header should track the runtime version from git."""

    monkeypatch.setattr(
        "bijux_agent.cli.helpers.uuid.uuid4",
        lambda: uuid.UUID(int=0),
    )
    monkeypatch.setattr("bijux_agent.cli.helpers.datetime", FixedDatetime)

    def build_with_version(version: str) -> dict[str, Any]:
        monkeypatch.setattr(
            "bijux_agent.utilities.version.get_runtime_version",
            lambda: version,
        )
        pipeline_result = _pipeline_result_template()
        _, trace = build_trace_from_result(
            pipeline_result=pipeline_result,
            file_path="stable.txt",
            task_goal="ensure trace",
            config={"model_metadata": asdict(default_model_metadata())},
            verdict=DecisionOutcome.PASS,
            confidence=float(pipeline_result["final_status"]["score"]),
            trace_dir=tmp_path / version,
            convergence_hash="stable-hash",
            convergence_reason="stability",
        )
        return trace.to_dict()

    first = build_with_version("tag-1")
    second = build_with_version("tag-2")

    assert first["runtime_version"] == "tag-1"
    assert second["runtime_version"] == "tag-2"
    assert first["runtime_version"] != second["runtime_version"]
