# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from pathlib import Path

from bijux_canon_ingest.interfaces.cli.entrypoint import main
from bijux_canon_ingest.interfaces.cli.pipeline_config import load_pipeline_config
from bijux_canon_ingest.interfaces.cli.pipeline_runner import boundary_app_config
from bijux_canon_ingest.interfaces.cli.typer_app import build_app
from bijux_canon_ingest.result import Err, Ok
import pytest


def test_load_pipeline_config_reads_step_definitions(tmp_path: Path) -> None:
    path = tmp_path / "pipeline.json"
    path.write_text(
        '{"steps":[{"name":"clean"},{"name":"chunk","params":{"chunk_size":128}}]}',
        encoding="utf-8",
    )

    config = load_pipeline_config(path)

    assert [step.name for step in config.steps] == ["clean", "chunk"]
    assert config.steps[1].params == {"chunk_size": 128}


def test_load_pipeline_config_rejects_invalid_shape(tmp_path: Path) -> None:
    path = tmp_path / "pipeline.json"
    path.write_text('{"steps":{"name":"clean"}}', encoding="utf-8")

    with pytest.raises(ValueError, match="config.steps must be a list"):
        load_pipeline_config(path)


def test_boundary_app_config_parses_debug_and_clean_rules() -> None:
    result = boundary_app_config(
        [
            "--input",
            "docs.csv",
            "--output",
            "chunks.jsonl",
            "--chunk_size",
            "256",
            "--clean_rules",
            "strip,upper",
            "--trace_docs",
            "--trace_chunks",
        ]
    )

    assert isinstance(result, Ok)
    config = result.value
    assert config.input_path == "docs.csv"
    assert config.output_path == "chunks.jsonl"
    assert config.ingest.env.chunk_size == 256
    assert config.ingest.clean.rule_names == ("strip", "upper")
    assert config.ingest.debug.trace_docs
    assert config.ingest.debug.trace_chunks


def test_boundary_app_config_returns_err_on_invalid_env() -> None:
    result = boundary_app_config(
        ["--input", "docs.csv", "--output", "chunks.jsonl", "--chunk_size", "0"]
    )

    assert isinstance(result, Err)
    assert "Invalid config" in result.error


def test_entrypoint_routes_retrieval_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, list[str]] = {}

    def fake_retrieval(argv: list[str]) -> int:
        seen["retrieval"] = argv
        return 7

    def fake_pipeline(argv: list[str]) -> int:
        seen["pipeline"] = argv
        return 3

    monkeypatch.setattr(
        "bijux_canon_ingest.interfaces.cli.entrypoint.run_retrieval_commands",
        fake_retrieval,
    )
    monkeypatch.setattr(
        "bijux_canon_ingest.interfaces.cli.entrypoint.run_pipeline_commands",
        fake_pipeline,
    )

    result = main(["retrieve", "--query", "powerhouse"])

    assert result == 7
    assert seen["retrieval"] == ["retrieve", "--query", "powerhouse"]
    assert "pipeline" not in seen


def test_entrypoint_routes_pipeline_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, list[str]] = {}

    def fake_retrieval(argv: list[str]) -> int:
        seen["retrieval"] = argv
        return 7

    def fake_pipeline(argv: list[str]) -> int:
        seen["pipeline"] = argv
        return 3

    monkeypatch.setattr(
        "bijux_canon_ingest.interfaces.cli.entrypoint.run_retrieval_commands",
        fake_retrieval,
    )
    monkeypatch.setattr(
        "bijux_canon_ingest.interfaces.cli.entrypoint.run_pipeline_commands",
        fake_pipeline,
    )

    result = main(["--input", "docs.csv", "--output", "chunks.jsonl"])

    assert result == 3
    assert seen["pipeline"] == ["--input", "docs.csv", "--output", "chunks.jsonl"]
    assert "retrieval" not in seen


class _FakeTyperApp:
    def __init__(self, **_: object) -> None:
        self.commands: dict[str, object] = {}

    def command(self, name: str | None = None):
        def register(func):
            self.commands[name or func.__name__.replace("_", "-")] = func
            return func

        return register


class _FakeTyperModule:
    def Typer(self, **kwargs: object) -> _FakeTyperApp:
        return _FakeTyperApp(**kwargs)


def test_typer_app_pipeline_command_routes_to_entrypoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, list[str]] = {}

    def fake_main(argv: list[str]) -> int:
        seen["argv"] = argv
        return 17

    monkeypatch.setattr(
        "bijux_canon_ingest.interfaces.cli.typer_app.importlib.import_module",
        lambda _: _FakeTyperModule(),
    )
    monkeypatch.setattr("bijux_canon_ingest.interfaces.cli.typer_app.main", fake_main)

    app = build_app()
    result = app.commands["pipeline"](
        input_csv=Path("docs.csv"),
        config=Path("pipeline.json"),
        set_values=["chunk.params.chunk_size=256", "clean.params.lower=false"],
        out=Path("chunks.jsonl"),
    )

    assert result == 17
    assert seen["argv"] == [
        "docs.csv",
        "--config",
        "pipeline.json",
        "--set",
        "chunk.params.chunk_size=256",
        "--set",
        "clean.params.lower=false",
        "--out",
        "chunks.jsonl",
    ]


def test_typer_app_ask_command_preserves_no_rerank_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, list[str]] = {}

    def fake_main(argv: list[str]) -> int:
        seen["argv"] = argv
        return 23

    monkeypatch.setattr(
        "bijux_canon_ingest.interfaces.cli.typer_app.importlib.import_module",
        lambda _: _FakeTyperModule(),
    )
    monkeypatch.setattr("bijux_canon_ingest.interfaces.cli.typer_app.main", fake_main)

    app = build_app()
    result = app.commands["ask"](
        index=Path("index.msgpack"),
        query="powerhouse",
        top_k=8,
        rerank=False,
        filters=["category=law"],
        format="yaml",
        out=Path("answer.yaml"),
    )

    assert result == 23
    assert seen["argv"] == [
        "ask",
        "--index",
        "index.msgpack",
        "--query",
        "powerhouse",
        "--top-k",
        "8",
        "--format",
        "yaml",
        "--no-rerank",
        "--filter",
        "category=law",
        "--out",
        "answer.yaml",
    ]
