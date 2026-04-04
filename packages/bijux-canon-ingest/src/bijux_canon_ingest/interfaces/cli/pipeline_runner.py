# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""CLI pipeline runner helpers."""

from __future__ import annotations

import argparse
from dataclasses import replace

from bijux_canon_ingest.config.app import AppConfig
from bijux_canon_ingest.config.cleaning import CleanConfig
from bijux_canon_ingest.config.ingest import IngestConfig, build_ingest_deps
from bijux_canon_ingest.core.types import Chunk, RagEnv, RawDoc
from bijux_canon_ingest.interfaces.cli.document_io import (
    CsvDocumentReader,
    write_chunks_jsonl,
)
from bijux_canon_ingest.application.pipeline import run_ingest_pipeline_docs
from bijux_canon_ingest.observability import DebugConfig
from bijux_canon_ingest.result import Err, Ok, Result, result_and_then, result_map


def boundary_app_config(args: list[str]) -> Result[AppConfig, str]:
    """Parse CLI args into frozen AppConfig."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--chunk_size", type=int, default=512)
    parser.add_argument("--clean_rules", default="strip,lower,collapse_ws")

    parser.add_argument("--trace_docs", action="store_true")
    parser.add_argument("--trace_kept", action="store_true")
    parser.add_argument("--trace_clean", action="store_true")
    parser.add_argument("--trace_chunks", action="store_true")
    parser.add_argument("--trace_embedded", action="store_true")
    parser.add_argument("--probe_chunks", action="store_true")

    ns = parser.parse_args(args)

    rule_names = tuple(x.strip() for x in ns.clean_rules.split(",") if x.strip())
    debug = DebugConfig(
        trace_docs=bool(ns.trace_docs),
        trace_kept=bool(ns.trace_kept),
        trace_clean=bool(ns.trace_clean),
        trace_chunks=bool(ns.trace_chunks),
        trace_embedded=bool(ns.trace_embedded),
        probe_chunks=bool(ns.probe_chunks),
    )

    try:
        cfg = IngestConfig(
            env=RagEnv(ns.chunk_size), clean=CleanConfig(rule_names=rule_names)
        )
    except Exception as exc:
        return Err(f"Invalid config: {exc}")

    cfg = replace(cfg, debug=debug)
    return Ok(AppConfig(input_path=ns.input, output_path=ns.output, ingest=cfg))


def read_docs(path: str) -> Result[list[RawDoc], str]:
    return CsvDocumentReader().read_docs(path)


def write_chunks(path: str, chunks: list[Chunk]) -> Result[None, str]:
    return write_chunks_jsonl(path, chunks)


def orchestrate(args: list[str]) -> Result[None, str]:
    return result_and_then(boundary_app_config(args), _run)


def _run(cfg: AppConfig) -> Result[None, str]:
    deps = build_ingest_deps(cfg.ingest)
    docs_res = read_docs(cfg.input_path)
    core_res = result_map(
        docs_res, lambda docs: run_ingest_pipeline_docs(docs, cfg.ingest, deps)
    )
    return result_and_then(core_res, lambda res: write_chunks(cfg.output_path, res[0]))


__all__ = ["boundary_app_config", "read_docs", "write_chunks", "orchestrate"]
