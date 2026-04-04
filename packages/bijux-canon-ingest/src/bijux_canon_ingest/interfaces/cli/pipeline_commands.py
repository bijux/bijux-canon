# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Pipeline-mode CLI commands for chunk generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from bijux_canon_ingest.application.pipeline_definitions.cli import (
    deep_merge,
    parse_override,
)
from bijux_canon_ingest.application.pipeline_definitions.configured import (
    PipelineConfig,
    StepConfig,
    build_rag_pipeline,
)
from bijux_canon_ingest.core.types import RawDoc
from bijux_canon_ingest.infra.adapters.file_storage import FileStorage
from bijux_canon_ingest.interfaces.cli.pipeline_config import load_pipeline_config
from bijux_canon_ingest.interfaces.cli.pipeline_parser import build_pipeline_parser
from bijux_canon_ingest.result.types import Err, ErrInfo, Ok, Result


def run_pipeline_commands(argv: list[str]) -> int:
    """Run the pipeline-oriented CLI mode."""

    args = build_pipeline_parser().parse_args(argv)

    config = _apply_overrides(
        config=load_pipeline_config(args.config),
        overrides=cast(list[str], args.overrides),
    )
    docs = _read_ok_docs(args.input_csv)
    if isinstance(docs, Err):
        return _render_error(docs)

    pipe = build_rag_pipeline(config)
    results = list(pipe(iter(docs.value)))
    for result in results:
        if isinstance(result, Err):
            return _render_error(result)

    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", encoding="utf-8") as handle:
            for result in results:
                if isinstance(result, Ok):
                    handle.write(
                        json.dumps(_chunk_to_json(result.value), ensure_ascii=False)
                    )
                    handle.write("\n")
    return 0


def _apply_overrides(*, config: PipelineConfig, overrides: list[str]) -> PipelineConfig:
    merged_overrides: dict[str, Any] = {}
    for override in overrides:
        merged_overrides = deep_merge(merged_overrides, parse_override(override))
    if not merged_overrides:
        return config

    steps: list[StepConfig] = []
    for step in config.steps:
        step_override = merged_overrides.get(step.name, {})
        if isinstance(step_override, dict):
            steps.append(
                StepConfig(
                    name=step.name,
                    params=deep_merge(dict(step.params), step_override),
                )
            )
            continue
        steps.append(step)
    return PipelineConfig(steps=tuple(steps))


def _read_ok_docs(path: Path) -> Result[list[RawDoc], ErrInfo]:
    storage = FileStorage()
    docs: list[RawDoc] = []
    for doc_result in storage.read_docs(str(path)):
        if isinstance(doc_result, Ok):
            docs.append(doc_result.value)
            continue
        return Err(doc_result.error)
    return Ok(docs)


def _render_error(result: Result[Any, ErrInfo]) -> int:
    if isinstance(result, Ok):
        return 0
    error = result.error
    print(
        json.dumps(
            {"error": {"code": error.code, "msg": error.msg, "stage": error.stage}},
            ensure_ascii=False,
        )
    )
    return 2 if error.code.startswith("PARSE") else 1


def _chunk_to_json(chunk: Any) -> dict[str, Any]:
    if hasattr(chunk, "metadata"):
        metadata = chunk.metadata
        try:
            metadata = dict(metadata)
        except Exception:
            metadata = {}
    else:
        metadata = {}
    return {
        "doc_id": getattr(chunk, "doc_id", ""),
        "text": getattr(chunk, "text", ""),
        "start": getattr(chunk, "start", 0),
        "end": getattr(chunk, "end", 0),
        "metadata": metadata,
        "embedding": list(getattr(chunk, "embedding", ())),
    }


__all__ = ["run_pipeline_commands"]
