# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Bijux RAG Core 6: minimal stdlib CLI shell (end-of-Bijux RAG).

# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false

This CLI is intentionally small and dependency-free (argparse). It demonstrates:
- thin shell adapter
- config-as-data loading (JSON)
- override parsing (dotted `a.b=1` strings)
- delegation to pure pipeline builders in `bijux_rag.pipelines`
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, cast

from bijux_rag.core.rag_types import RagEnv, RawDoc
from bijux_rag.infra.adapters.file_storage import FileStorage
from bijux_rag.pipelines.cli import deep_merge, parse_override
from bijux_rag.pipelines.configured import PipelineConfig, StepConfig, build_rag_pipeline
from bijux_rag.rag.app import RagBuildConfig, build_index_from_csv, parse_filters
from bijux_rag.rag.app import ask as rag_ask
from bijux_rag.rag.app import retrieve as rag_retrieve
from bijux_rag.result.types import Err, ErrInfo, Ok, Result


def _load_config(path: Path) -> PipelineConfig:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "steps" not in data:
        raise ValueError("config must be an object with a 'steps' field")
    steps_raw: list[dict[str, Any]] = data["steps"]
    if not isinstance(steps_raw, list):
        raise ValueError("config.steps must be a list")
    steps: list[StepConfig] = []
    for s in steps_raw:
        if not isinstance(s, dict) or "name" not in s:
            raise ValueError("each step must be an object with a 'name'")
        name: Any = s["name"]
        params: Any = s.get("params", {})
        if not isinstance(name, str) or not isinstance(params, dict):
            raise ValueError("step.name must be str and step.params must be object")
        steps.append(StepConfig(name=name, params=params))
    return PipelineConfig(steps=tuple(steps))


def _render(result: Result[Any, ErrInfo]) -> int:
    if isinstance(result, Ok):
        return 0
    err = result.error
    print(
        json.dumps(
            {"error": {"code": err.code, "msg": err.msg, "stage": err.stage}}, ensure_ascii=False
        )
    )
    return 2 if err.code.startswith("PARSE") else 1


def _chunk_to_json(chunk: Any) -> dict[str, Any]:
    if hasattr(chunk, "metadata"):
        meta = chunk.metadata
        try:
            meta = dict(meta)
        except Exception:
            meta = {}
    else:
        meta = {}
    return {
        "doc_id": getattr(chunk, "doc_id", ""),
        "text": getattr(chunk, "text", ""),
        "start": getattr(chunk, "start", 0),
        "end": getattr(chunk, "end", 0),
        "metadata": meta,
        "embedding": list(getattr(chunk, "embedding", ())),
    }


def _main_legacy(argv: list[str]) -> int:
    """Legacy ingestion pipeline CLI.

    Kept for compatibility with existing tests and to avoid breaking users.
    New RAG commands are under explicit subcommands.
    """

    p = argparse.ArgumentParser(prog="bijux-rag")
    p.add_argument("input_csv", type=Path)
    p.add_argument("--config", type=Path, required=True)
    p.add_argument(
        "--set", dest="overrides", action="append", default=[], help="Override a.b.c=value"
    )
    p.add_argument("--out", type=Path, default=None, help="Optional output JSONL path for chunks")
    args = p.parse_args(argv)

    cfg = _load_config(args.config)
    overrides: dict[str, Any] = {}
    for ov in cast(list[str], args.overrides):
        overrides = deep_merge(overrides, parse_override(ov))

    if overrides:
        steps: list[StepConfig] = []
        for step in cfg.steps:
            step_over = overrides.get(step.name, {})
            if isinstance(step_over, dict):
                steps.append(
                    StepConfig(name=step.name, params=deep_merge(dict(step.params), step_over))
                )
            else:
                steps.append(step)
        cfg = PipelineConfig(steps=tuple(steps))

    storage = FileStorage()
    docs = storage.read_docs(str(args.input_csv))

    ok_docs: list[RawDoc] = []
    for doc_res in docs:
        if isinstance(doc_res, Ok):
            ok_docs.append(doc_res.value)
        else:
            return _render(Err(doc_res.error))

    pipe = build_rag_pipeline(cfg)
    results = list(pipe(iter(ok_docs)))
    for out_res in results:
        if isinstance(out_res, Err):
            return _render(out_res)

    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", encoding="utf-8") as f_out:
            for res in results:
                if isinstance(res, Ok):
                    f_out.write(json.dumps(_chunk_to_json(res.value), ensure_ascii=False))
                    f_out.write("\n")
    return 0


def _main_rag(argv: list[str]) -> int:
    """RAG-capable CLI: index, retrieve, ask, eval."""

    p = argparse.ArgumentParser(prog="bijux-rag")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_index = sub.add_parser("index", help="Index operations")
    sub_index = p_index.add_subparsers(dest="index_cmd", required=True)
    p_build = sub_index.add_parser("build", help="Build an index from CSV")
    p_build.add_argument("--input", type=Path, required=True)
    p_build.add_argument("--out", type=Path, required=True)
    p_build.add_argument("--backend", choices=["bm25", "numpy-cosine"], default="bm25")
    p_build.add_argument("--embedder", choices=["hash16", "sbert"], default="hash16")
    p_build.add_argument("--sbert-model", default="all-MiniLM-L6-v2")
    p_build.add_argument("--bm25-buckets", type=int, default=2048)
    p_build.add_argument("--chunk-size", type=int, default=128)
    p_build.add_argument("--overlap", type=int, default=0)
    p_build.add_argument("--tail-policy", default="emit_short")

    p_retrieve = sub.add_parser("retrieve", help="Retrieve top-k chunks")
    p_retrieve.add_argument("--index", type=Path, required=True)
    p_retrieve.add_argument("--query", required=True)
    p_retrieve.add_argument("--top-k", type=int, default=5)
    p_retrieve.add_argument("--filter", action="append", default=[], help="Filter k=v (repeatable)")
    p_retrieve.add_argument("--out", type=Path, default=None)

    p_ask = sub.add_parser("ask", help="Answer with citations (extractive)")
    p_ask.add_argument("--index", type=Path, required=True)
    p_ask.add_argument("--query", required=True)
    p_ask.add_argument("--top-k", type=int, default=5)
    p_ask.add_argument("--filter", action="append", default=[], help="Filter k=v (repeatable)")
    p_ask.add_argument("--no-rerank", action="store_true")
    p_ask.add_argument("--format", choices=["json", "yaml"], default="json")
    p_ask.add_argument("--out", type=Path, default=None)

    p_eval = sub.add_parser("eval", help="Evaluate retrieval vs a query suite")
    p_eval.add_argument("--index", type=Path, required=True)
    p_eval.add_argument(
        "--suite", type=Path, required=True, help="Directory containing queries.jsonl"
    )
    p_eval.add_argument("--k", type=int, default=10)
    p_eval.add_argument(
        "--baseline", type=Path, default=None, help="Optional baseline metrics JSON"
    )
    p_eval.add_argument("--tolerance", type=float, default=0.0)

    args = p.parse_args(argv)

    if args.cmd == "index" and args.index_cmd == "build":
        env = RagEnv(chunk_size=args.chunk_size, overlap=args.overlap, tail_policy=args.tail_policy)
        cfg = RagBuildConfig(
            chunk_env=env,
            backend=args.backend,
            embedder=args.embedder,
            sbert_model=args.sbert_model,
            bm25_buckets=int(args.bm25_buckets),
        )
        args.out.parent.mkdir(parents=True, exist_ok=True)
        fp = build_index_from_csv(csv_path=args.input, out_path=args.out, cfg=cfg)
        print(
            json.dumps(
                {"index": str(args.out), "fingerprint": fp, "backend": args.backend},
                ensure_ascii=False,
            )
        )
        return 0

    if args.cmd == "retrieve":
        filt = parse_filters(list(args.filter))
        cands = rag_retrieve(
            index_path=args.index, query=args.query, top_k=args.top_k, filters=filt
        )
        payload = {
            "candidates": [
                {
                    "doc_id": c.chunk.doc_id,
                    "chunk_id": c.chunk.chunk_id,
                    "text": c.chunk.text,
                    "start": c.chunk.start,
                    "end": c.chunk.end,
                    "metadata": dict(c.chunk.metadata),
                    "score": float(c.score),
                }
                for c in cands
            ]
        }
        out_s = json.dumps(payload, ensure_ascii=False)
        if args.out is None:
            print(out_s)
        else:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(out_s + "\n", encoding="utf-8")
        return 0

    if args.cmd == "ask":
        filt = parse_filters(list(args.filter))
        ans = rag_ask(
            index_path=args.index,
            query=args.query,
            top_k=args.top_k,
            filters=filt,
            rerank=not args.no_rerank,
        )
        ask_payload: dict[str, object] = {
            "text": ans.text,
            "citations": [
                {"doc_id": c.doc_id, "chunk_id": c.chunk_id, "start": c.start, "end": c.end}
                for c in ans.citations
            ],
        }

        if args.format == "yaml":
            try:
                import yaml
            except Exception as e:
                raise SystemExit("YAML output requires PyYAML") from e
            out_s = yaml.safe_dump(ask_payload, sort_keys=False, allow_unicode=True)
        else:
            out_s = json.dumps(ask_payload, ensure_ascii=False)

        if args.out is None:
            print(out_s)
        else:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(
                out_s + ("\n" if not out_s.endswith("\n") else ""), encoding="utf-8"
            )
        return 0

    if args.cmd == "eval":
        # Expect queries.jsonl lines: {"query": "...", "relevant_doc_ids": ["..."]}
        qpath = args.suite / "queries.jsonl"
        if not qpath.exists():
            print(
                json.dumps({"error": {"code": "MISSING_SUITE", "msg": "queries.jsonl not found"}})
            )
            return 2
        queries: list[dict[str, Any]] = []
        for line in qpath.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            queries.append(json.loads(line))

        k = max(1, int(args.k))
        hits = 0
        total = 0
        for q in queries:
            query = str(q.get("query", ""))
            rel = set(map(str, q.get("relevant_doc_ids", [])))
            if not query or not rel:
                continue
            cands = rag_retrieve(index_path=args.index, query=query, top_k=k)
            got = {c.chunk.doc_id for c in cands}
            hits += int(len(got & rel) > 0)
            total += 1

        recall_at_k = hits / total if total else 0.0
        metrics = {"recall_at_k": recall_at_k, "k": k, "num_queries": total}

        if args.baseline is not None:
            base = json.loads(args.baseline.read_text(encoding="utf-8"))
            base_r = float(base.get("recall_at_k", 0.0))
            tol = float(args.tolerance)
            if recall_at_k + tol < base_r:
                print(
                    json.dumps(
                        {"metrics": metrics, "baseline": base, "status": "REGRESSION"},
                        ensure_ascii=False,
                    )
                )
                return 1
        print(json.dumps({"metrics": metrics, "status": "OK"}, ensure_ascii=False))
        return 0

    raise SystemExit("unreachable")


def main(argv: list[str] | None = None) -> int:
    argv_list = list(sys.argv[1:] if argv is None else argv)
    if argv_list and argv_list[0] in {"index", "retrieve", "ask", "eval"}:
        return _main_rag(argv_list)
    return _main_legacy(argv_list)


__all__ = ["main"]
