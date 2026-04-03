# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""
100 E2E regression gates for a truthful RAG.

Design goals (CI-safe):
- Offline + deterministic (use profile="ci", backend="bm25", extractive generator).
- Tests must FAIL if bijux-rag is not a real RAG (index/retrieve/ask/citations/persistence).
- 25 pinned queries × 4 essential assertions = 100 tests.

Hard contract this suite enforces:
1) Index can be built, saved, loaded (persistence is part of fixture).
2) retrieve() returns expected doc(s) in top-5 and top-10.
3) ask() returns non-empty answer + citations.
4) Every citation maps to returned contexts with valid spans.
5) CI profile is deterministic (retrieve + ask stable over repeated runs).

Required suite assets:
- tests/eval/corpus.jsonl
- tests/eval/queries.jsonl (must contain exactly 25 queries)
"""

from __future__ import annotations

import json
from dataclasses import is_dataclass
from pathlib import Path
from typing import Any, Iterable

import pytest

from bijux_rag.core.rag_types import RawDoc
from bijux_rag.result import Err, Ok

pytestmark = [pytest.mark.e2e]


# -----------------------------
# Helpers (robust to dict/dataclass/objects)
# -----------------------------


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


def _unwrap_ok(val: Any, *, what: str) -> Any:
    if isinstance(val, Ok):
        return val.value
    if isinstance(val, Err):
        pytest.fail(f"{what} returned Err: {val.error}")
    return val


def _doc_id(item: Any) -> str:
    # Candidate/Context/Citation must expose doc_id (preferred) or id as fallback.
    v = _get(item, "doc_id", None)
    if v is None:
        v = _get(item, "id", "")
    return str(v)


def _text(item: Any) -> str:
    return str(_get(item, "text", _get(item, "chunk", _get(item, "content", ""))))


def _span(item: Any) -> tuple[int, int]:
    s = _get(item, "start", 0)
    e = _get(item, "end", 0)
    try:
        return int(s), int(e)
    except Exception:
        return 0, 0


def _as_candidates(res: Any) -> list[Any]:
    # retrieve() may return list[Candidate] or {"candidates":[...]} or an object with .candidates
    if isinstance(res, list):
        return res
    c = _get(res, "candidates", None)
    if isinstance(c, list):
        return c
    return []


def _ask_answer_text(res: Any) -> str:
    # ask() may return {"answer": "..."} or {"text": "..."} or Answer.text/answer
    v = _get(res, "answer", None)
    if v is None:
        v = _get(res, "text", "")
    return str(v)


def _ask_citations(res: Any) -> list[Any]:
    c = _get(res, "citations", None)
    if isinstance(c, list):
        return c
    return []


def _ask_contexts(res: Any) -> list[Any]:
    # ask() must return contexts used for grounding verification
    ctx = _get(res, "contexts", None)
    if isinstance(ctx, list):
        return ctx
    ctx = _get(res, "candidates", None)
    if isinstance(ctx, list):
        return ctx
    return []


# -----------------------------
# Param set: exactly 25 queries => 25*4 = 100 tests
# -----------------------------


def _load_query_ids() -> list[str]:
    base = Path(__file__).resolve().parents[1] / "eval" / "queries.jsonl"
    ids: list[str] = []
    for row in _load_jsonl(base):
        ids.append(str(row["id"]))
    if len(ids) != 25:
        raise RuntimeError(
            f"Expected exactly 25 queries in tests/eval/queries.jsonl, got {len(ids)}. "
            "This suite is defined as 25×4=100 essential E2E tests."
        )
    return ids


_QUERY_IDS = _load_query_ids()
_CASES = [pytest.param(i, id=_QUERY_IDS[i]) for i in range(25)]


# -----------------------------
# Fixtures: build + save + load index (persistence is enforced)
# -----------------------------


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

    queries: list[dict[str, Any]] = []
    for row in query_rows:
        expected = row.get("expected_doc_ids", [])
        if not isinstance(expected, list) or not all(isinstance(x, str) for x in expected):
            raise TypeError(f"expected_doc_ids must be list[str] for query {row.get('id')}")
        queries.append(
            {
                "id": str(row["id"]),
                "query": str(row["query"]),
                "expected_doc_ids": expected,
                "tags": list(row.get("tags", [])),
            }
        )

    return {"docs": docs, "queries": queries}


@pytest.fixture(scope="session")
def rag_app() -> Any:
    """
    Requires: bijux_rag.rag.app.RagApp(profile="ci") with methods:
      - build_index(docs, backend, chunk_size, overlap, tail_policy)
      - save_index(index, path)
      - load_index(path)
      - retrieve(index, query, top_k, filters=None)
      - ask(index, query, top_k, filters=None)
    """
    try:
        from bijux_rag.rag.app import RagApp  # type: ignore
    except Exception as exc:
        pytest.fail(
            "Missing bijux_rag.rag.app.RagApp. This suite enforces real RAG primitives "
            f"(index/retrieve/ask). Import error: {exc}"
        )

    app = RagApp(profile="ci")
    # Hard gate: required callables must exist.
    for name in ("build_index", "save_index", "load_index", "retrieve", "ask"):
        if not callable(getattr(app, name, None)):
            pytest.fail(f"RagApp must implement callable {name}() for E2E RAG gates.")
    return app


@pytest.fixture(scope="session")
def rag_index(
    tmp_path_factory: pytest.TempPathFactory,
    rag_app: Any,
    rag_eval_suite: dict[str, Any],
) -> Any:
    docs: Iterable[RawDoc] = rag_eval_suite["docs"]
    tmp_dir = tmp_path_factory.mktemp("rag-index")
    index_path = tmp_dir / "index.msgpack"

    # Enforce persistence as part of setup:
    # - build -> save -> load must work deterministically.
    index0 = _unwrap_ok(
        rag_app.build_index(
            docs,
            backend="bm25",
            chunk_size=4096,
            overlap=0,
            tail_policy="emit_short",
        ),
        what="build_index",
    )
    _unwrap_ok(rag_app.save_index(index0, index_path), what="save_index")
    index1 = _unwrap_ok(rag_app.load_index(index_path), what="load_index")
    return index1


# -----------------------------
# The 100 essential E2E tests
# -----------------------------


@pytest.mark.parametrize("case", _CASES)
def test_retrieve_top5_contains_expected(
    rag_app: Any, rag_index: Any, rag_eval_suite: dict[str, Any], case: int
) -> None:
    q = rag_eval_suite["queries"][case]
    res = _unwrap_ok(rag_app.retrieve(rag_index, q["query"], top_k=5), what="retrieve")
    cands = _as_candidates(res)
    got = {_doc_id(c) for c in cands}
    assert got & set(q["expected_doc_ids"]), (
        f"Expected one of {q['expected_doc_ids']} in top-5; got={sorted(got)}"
    )


@pytest.mark.parametrize("case", _CASES)
def test_retrieve_top10_contains_expected(
    rag_app: Any, rag_index: Any, rag_eval_suite: dict[str, Any], case: int
) -> None:
    q = rag_eval_suite["queries"][case]
    res = _unwrap_ok(rag_app.retrieve(rag_index, q["query"], top_k=10), what="retrieve")
    cands = _as_candidates(res)
    got = {_doc_id(c) for c in cands}
    assert got & set(q["expected_doc_ids"]), (
        f"Expected one of {q['expected_doc_ids']} in top-10; got={sorted(got)}"
    )


@pytest.mark.parametrize("case", _CASES)
def test_ask_returns_answer_and_grounded_citations(
    rag_app: Any, rag_index: Any, rag_eval_suite: dict[str, Any], case: int
) -> None:
    q = rag_eval_suite["queries"][case]
    res = _unwrap_ok(rag_app.ask(rag_index, q["query"], top_k=5), what="ask")

    answer = _ask_answer_text(res)
    assert answer.strip(), "ask() must return non-empty answer text"

    citations = _ask_citations(res)
    assert citations, "ask() must return citations in CI profile"

    contexts = _ask_contexts(res)
    assert contexts, "ask() must return contexts/candidates used for grounding verification"

    # Citations must cite at least one expected doc for this query.
    cited_docs = {_doc_id(c) for c in citations}
    assert cited_docs & set(q["expected_doc_ids"]), (
        f"Expected citations to include {q['expected_doc_ids']}; got={sorted(cited_docs)}"
    )

    # Every citation must map to returned contexts and have valid spans.
    ctx_by_doc: dict[str, list[Any]] = {}
    for ctx in contexts:
        ctx_by_doc.setdefault(_doc_id(ctx), []).append(ctx)

    for cit in citations:
        did = _doc_id(cit)
        assert did in ctx_by_doc, f"citation doc_id={did} not in returned contexts"
        s, e = _span(cit)
        assert 0 <= s <= e, f"invalid citation span: {(s, e)}"

        # Span must fit within at least one returned context text for that doc.
        ok = False
        for ctx in ctx_by_doc[did]:
            t = _text(ctx)
            if t and e <= len(t):
                ok = True
                break
        assert ok, f"citation span {(s, e)} does not fit any returned context for doc_id={did}"


@pytest.mark.parametrize("case", _CASES)
def test_ci_profile_is_deterministic(
    rag_app: Any, rag_index: Any, rag_eval_suite: dict[str, Any], case: int
) -> None:
    q = rag_eval_suite["queries"][case]
    query = q["query"]

    r1 = _unwrap_ok(rag_app.retrieve(rag_index, query, top_k=10), what="retrieve")
    r2 = _unwrap_ok(rag_app.retrieve(rag_index, query, top_k=10), what="retrieve")
    c1 = [_doc_id(c) for c in _as_candidates(r1)]
    c2 = [_doc_id(c) for c in _as_candidates(r2)]
    assert c1 == c2, "retrieve() must be deterministic in CI profile"

    a1 = _unwrap_ok(rag_app.ask(rag_index, query, top_k=5), what="ask")
    a2 = _unwrap_ok(rag_app.ask(rag_index, query, top_k=5), what="ask")
    assert _ask_answer_text(a1) == _ask_answer_text(a2), (
        "ask() answer text must be deterministic in CI profile"
    )

    cits1 = [(_doc_id(c), *_span(c)) for c in _ask_citations(a1)]
    cits2 = [(_doc_id(c), *_span(c)) for c in _ask_citations(a2)]
    assert cits1 == cits2, "ask() citations must be deterministic in CI profile"
