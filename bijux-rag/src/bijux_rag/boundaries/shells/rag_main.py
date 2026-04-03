# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Thin orchestrator example for the end-of-Bijux RAG codebase.

# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
"""

from __future__ import annotations

import argparse
from dataclasses import replace

from bijux_rag.boundaries.app_config import AppConfig
from bijux_rag.boundaries.shells.rag_api_shell import FSReader, write_chunks_jsonl
from bijux_rag.core.rag_types import Chunk, RagEnv, RawDoc
from bijux_rag.rag.clean_cfg import CleanConfig
from bijux_rag.rag.config import RagConfig, get_deps
from bijux_rag.rag.rag_api import full_rag_api_docs
from bijux_rag.rag.types import DebugConfig
from bijux_rag.result import Err, Ok, Result, result_and_then, result_map


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
        cfg = RagConfig(env=RagEnv(ns.chunk_size), clean=CleanConfig(rule_names=rule_names))
    except Exception as exc:
        return Err(f"Invalid config: {exc}")

    cfg = replace(cfg, debug=debug)
    return Ok(AppConfig(input_path=ns.input, output_path=ns.output, rag=cfg))


def read_docs(path: str) -> Result[list[RawDoc], str]:
    return FSReader().read_docs(path)


def write_chunks(path: str, chunks: list[Chunk]) -> Result[None, str]:
    return write_chunks_jsonl(path, chunks)


def orchestrate(args: list[str]) -> Result[None, str]:
    return result_and_then(boundary_app_config(args), _run)


def _run(cfg: AppConfig) -> Result[None, str]:
    deps = get_deps(cfg.rag)
    docs_res = read_docs(cfg.input_path)
    core_res = result_map(docs_res, lambda docs: full_rag_api_docs(docs, cfg.rag, deps))
    return result_and_then(core_res, lambda res: write_chunks(cfg.output_path, res[0]))


__all__ = ["boundary_app_config", "read_docs", "write_chunks", "orchestrate"]
