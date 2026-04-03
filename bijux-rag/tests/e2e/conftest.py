# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""E2E fixtures that enforce 'truthful RAG' behavior.

These tests are intentionally strict and offline/deterministic.
They are designed to FAIL until bijux-rag implements real RAG primitives:

* index build + save + load
* retrieve(query) -> ranked contexts
* ask(query) -> answer text + grounded citations that map to returned contexts

If these fixtures fail, it means bijux-rag is still 'ingestion-only' and not a RAG.
"""

from __future__ import annotations

import json
from dataclasses import is_dataclass
from pathlib import Path
from typing import Any, Iterable

import pytest

from bijux_rag.core.rag_types import RawDoc
from bijux_rag.result import Err, Ok


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        if not isinstance(obj, dict):
            raise TypeError(f"JSONL row must be an object: {path}")
        rows.append(obj)
    return rows


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    if is_dataclass(obj):
        return getattr(obj, key, default)
    return getattr(obj, key, default)


def _unwrap_ok(maybe_result: Any, *, what: str) -> Any:
    """Accept either a bijux Result (Ok/Err) or a raw value."""

    if isinstance(maybe_result, Ok):
        return maybe_result.value
    if isinstance(maybe_result, Err):
        pytest.fail(f"{what} returned Err: {maybe_result.error}")
    return maybe_result


@pytest.fixture(scope="session")
def rag_eval_suite() -> dict[str, Any]:
    base = Path(__file__).resolve().parents[1] / "eval"
    corpus_path = base / "corpus.jsonl"
    queries_path = base / "queries.jsonl"

    corpus_rows = _load_jsonl(corpus_path)
    query_rows = _load_jsonl(queries_path)

    docs: list[RawDoc] = []
    for row in corpus_rows:
        docs.append(
            RawDoc(
                doc_id=str(row["doc_id"]),
                title=str(row.get("title", "")),
                abstract=str(row.get("abstract", "")),
                categories=str(row.get("categories", "")),
            )
        )

    # Normalize query structure.
    queries: list[dict[str, Any]] = []
    for row in query_rows:
        qid = str(row["id"])
        query = str(row["query"])
        expected = row.get("expected_doc_ids", [])
        if not isinstance(expected, list) or not all(isinstance(x, str) for x in expected):
            raise TypeError(f"expected_doc_ids must be list[str] for query {qid}")
        queries.append(
            {
                "id": qid,
                "query": query,
                "expected_doc_ids": expected,
                "tags": list(row.get("tags", [])),
            }
        )

    return {"docs": docs, "queries": queries}


@pytest.fixture(scope="session")
def rag_app() -> Any:
    """Requires you to implement bijux_rag.rag.app.RagApp (truthful RAG entrypoint)."""

    try:
        from bijux_rag.rag.app import RagApp  # type: ignore
    except Exception as exc:  # pragma: no cover
        pytest.fail(
            "Missing bijux_rag.rag.app.RagApp. Implement real RAG primitives (index/retrieve/ask) first. "
            f"Import error: {exc}"
        )
    return RagApp(profile="ci")


@pytest.fixture(scope="session")
def rag_index(
    tmp_path_factory: pytest.TempPathFactory, rag_app: Any, rag_eval_suite: dict[str, Any]
) -> Any:
    """Build + save + load a deterministic offline index (must be reproducible)."""

    docs: Iterable[RawDoc] = rag_eval_suite["docs"]
    tmp_dir = tmp_path_factory.mktemp("rag-index")
    index_path = tmp_dir / "index.msgpack"

    # Required contract:
    # - build_index(docs, backend=..., chunk_size=..., overlap=..., tail_policy=...) -> Ok(index)
    # - save_index(index, path) -> Ok(None)
    # - load_index(path) -> Ok(index)
    build = getattr(rag_app, "build_index", None)
    save = getattr(rag_app, "save_index", None)
    load = getattr(rag_app, "load_index", None)

    if not callable(build) or not callable(save) or not callable(load):
        pytest.fail("RagApp must implement build_index/save_index/load_index")

    index0 = _unwrap_ok(
        build(
            docs,
            backend="bm25",
            chunk_size=4096,
            overlap=0,
            tail_policy="emit_short",
        ),
        what="build_index",
    )

    _unwrap_ok(save(index0, index_path), what="save_index")
    index1 = _unwrap_ok(load(index_path), what="load_index")
    return index1


__all__ = [
    "rag_eval_suite",
    "rag_app",
    "rag_index",
    "_get",
    "_unwrap_ok",
]
