# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Retrieval-mode CLI commands for indexes, search, and evaluation."""

from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
from typing import Any, cast

from bijux_canon_ingest.application.indexing import (
    IndexBuildConfig,
    build_index_from_docs,
)
from bijux_canon_ingest.application.querying import ask as rag_ask
from bijux_canon_ingest.application.querying import parse_filters
from bijux_canon_ingest.application.querying import retrieve as rag_retrieve
from bijux_canon_ingest.core.types import RagEnv, RawDoc
from bijux_canon_ingest.infra.adapters.file_storage import FileStorage
from bijux_canon_ingest.interfaces.cli.retrieval_output import (
    YamlModule,
    render_answer_output,
    render_retrieve_output,
    write_output,
)
from bijux_canon_ingest.interfaces.cli.retrieval_parser import build_retrieval_parser
from bijux_canon_ingest.result import Err


def run_retrieval_commands(argv: list[str]) -> int:
    """Run the retrieval-oriented CLI mode."""

    args = build_retrieval_parser().parse_args(argv)
    if args.cmd == "index" and args.index_cmd == "build":
        return _run_build(args)
    if args.cmd == "retrieve":
        return _run_retrieve(args)
    if args.cmd == "ask":
        return _run_ask(args)
    if args.cmd == "eval":
        return _run_eval(args)
    raise SystemExit("unreachable")


def _run_build(args: argparse.Namespace) -> int:
    env = RagEnv(
        chunk_size=args.chunk_size,
        overlap=args.overlap,
        tail_policy=args.tail_policy,
    )
    config = IndexBuildConfig(
        chunk_env=env,
        backend=args.backend,
        embedder=args.embedder,
        sbert_model=args.sbert_model,
        bm25_buckets=int(args.bm25_buckets),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fingerprint = build_index_from_docs(
        docs=_read_docs(args.input),
        out_path=str(args.out),
        cfg=config,
    )
    print(
        json.dumps(
            {
                "index": str(args.out),
                "fingerprint": fingerprint,
                "backend": args.backend,
            },
            ensure_ascii=False,
        )
    )
    return 0


def _read_docs(path: Path) -> list[RawDoc]:
    docs: list[RawDoc] = []
    errors: list[str] = []
    for result in FileStorage().read_docs(str(path)):
        if isinstance(result, Err):
            errors.append(f"{result.error.code}: {result.error.msg}")
            continue
        docs.append(result.value)
    if errors:
        raise ValueError("CSV parse failures: " + "; ".join(errors[:3]))
    return docs


def _run_retrieve(args: argparse.Namespace) -> int:
    filters = parse_filters(list(args.filter))
    candidates = rag_retrieve(
        index_path=args.index,
        query=args.query,
        top_k=args.top_k,
        filters=filters,
    )
    return write_output(
        payload=render_retrieve_output(candidates),
        out_path=args.out,
    )


def _run_ask(args: argparse.Namespace) -> int:
    filters = parse_filters(list(args.filter))
    answer = rag_ask(
        index_path=args.index,
        query=args.query,
        top_k=args.top_k,
        filters=filters,
        rerank=not args.no_rerank,
    )
    if args.format == "yaml":
        try:
            yaml_module = cast(YamlModule, importlib.import_module("yaml"))
        except ModuleNotFoundError as exc:
            raise SystemExit("YAML output requires PyYAML") from exc
        output = render_answer_output(
            answer,
            output_format="yaml",
            yaml_module=yaml_module,
        )
    else:
        output = render_answer_output(answer, output_format="json")
    return write_output(payload=output, out_path=args.out)


def _run_eval(args: argparse.Namespace) -> int:
    query_path = args.suite / "queries.jsonl"
    if not query_path.exists():
        print(
            json.dumps(
                {
                    "error": {
                        "code": "MISSING_SUITE",
                        "msg": "queries.jsonl not found",
                    }
                }
            )
        )
        return 2

    queries: list[dict[str, Any]] = []
    for line in query_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            queries.append(json.loads(line))

    top_k = max(1, int(args.k))
    hits = 0
    total = 0
    for query_row in queries:
        query = str(query_row.get("query", ""))
        relevant_doc_ids = set(map(str, query_row.get("relevant_doc_ids", [])))
        if not query or not relevant_doc_ids:
            continue
        candidates = rag_retrieve(index_path=args.index, query=query, top_k=top_k)
        doc_ids = {candidate.chunk.doc_id for candidate in candidates}
        hits += int(len(doc_ids & relevant_doc_ids) > 0)
        total += 1

    recall_at_k = hits / total if total else 0.0
    metrics = {"recall_at_k": recall_at_k, "k": top_k, "num_queries": total}
    if args.baseline is not None:
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        baseline_recall = float(baseline.get("recall_at_k", 0.0))
        tolerance = float(args.tolerance)
        if recall_at_k + tolerance < baseline_recall:
            print(
                json.dumps(
                    {"metrics": metrics, "baseline": baseline, "status": "REGRESSION"},
                    ensure_ascii=False,
                )
            )
            return 1
    print(json.dumps({"metrics": metrics, "status": "OK"}, ensure_ascii=False))
    return 0


__all__ = ["run_retrieval_commands"]
