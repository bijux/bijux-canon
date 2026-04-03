# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""100 E2E gates that force bijux-rag to be a real RAG.

Offline + deterministic by design.

These tests will FAIL until bijux-rag implements:
  - RagApp.build_index / save_index / load_index
  - RagApp.retrieve
  - RagApp.ask

Truthfulness contract:
  - retrieval must surface expected docs for a pinned suite
  - ask must return citations
  - citations must map to returned contexts (no hallucinated sources)
  - ci profile must be deterministic
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tests.e2e.conftest import _get, _unwrap_ok


def _load_query_ids() -> list[str]:
    """Load query ids at collection time to create stable, readable test ids."""

    base = Path(__file__).resolve().parents[1] / "eval" / "queries.jsonl"
    ids: list[str] = []
    for line in base.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        ids.append(str(row["id"]))
    if len(ids) != 25:
        raise RuntimeError("This suite expects exactly 25 queries (25×4 = 100 tests).")
    return ids


_QUERY_IDS = _load_query_ids()


def _doc_id(item: Any) -> str:
    return str(_get(item, "doc_id", _get(item, "id", "")))


def _span(item: Any) -> tuple[int, int]:
    s = _get(item, "start", 0)
    e = _get(item, "end", 0)
    try:
        return int(s), int(e)
    except Exception:
        return 0, 0


def _text(item: Any) -> str:
    v = _get(item, "text", "")
    return str(v)


def _candidates_from_retrieve(res: Any) -> list[Any]:
    # Accept either list[Candidate] or {"candidates": [...]}.
    if isinstance(res, list):
        return res
    cands = _get(res, "candidates", None)
    if isinstance(cands, list):
        return cands
    return []


def _answer_text(res: Any) -> str:
    # Accept {"answer": "..."} or {"text": "..."} or Answer.text
    v = _get(res, "answer", None)
    if v is None:
        v = _get(res, "text", "")
    return str(v)


def _citations_from_ask(res: Any) -> list[Any]:
    cits = _get(res, "citations", None)
    if isinstance(cits, list):
        return cits
    return []


def _contexts_from_ask(res: Any) -> list[Any]:
    # Require ask() to return the grounded contexts for verification.
    ctx = _get(res, "contexts", None)
    if isinstance(ctx, list):
        return ctx
    ctx = _get(res, "candidates", None)
    if isinstance(ctx, list):
        return ctx
    return []


_CASE_PARAMS = [pytest.param(i, id=_QUERY_IDS[i]) for i in range(25)]


# --- The 100 gates ---


@pytest.mark.e2e
@pytest.mark.parametrize("case", _CASE_PARAMS)
def test_retrieve_top5_contains_expected(
    rag_app: Any, rag_index: Any, rag_eval_suite: dict[str, Any], case: int
) -> None:
    q = rag_eval_suite["queries"][case]
    res = _unwrap_ok(rag_app.retrieve(rag_index, q["query"], top_k=5), what="retrieve")
    cands = _candidates_from_retrieve(res)
    got = {_doc_id(c) for c in cands}
    assert got & set(q["expected_doc_ids"]), (
        f"expected one of {q['expected_doc_ids']} in top-5; got={sorted(got)}"
    )


@pytest.mark.e2e
@pytest.mark.parametrize("case", _CASE_PARAMS)
def test_retrieve_top10_contains_expected(
    rag_app: Any, rag_index: Any, rag_eval_suite: dict[str, Any], case: int
) -> None:
    q = rag_eval_suite["queries"][case]
    res = _unwrap_ok(rag_app.retrieve(rag_index, q["query"], top_k=10), what="retrieve")
    cands = _candidates_from_retrieve(res)
    got = {_doc_id(c) for c in cands}
    assert got & set(q["expected_doc_ids"]), (
        f"expected one of {q['expected_doc_ids']} in top-10; got={sorted(got)}"
    )


@pytest.mark.e2e
@pytest.mark.parametrize("case", _CASE_PARAMS)
def test_ask_has_grounded_citations(
    rag_app: Any, rag_index: Any, rag_eval_suite: dict[str, Any], case: int
) -> None:
    q = rag_eval_suite["queries"][case]
    res = _unwrap_ok(rag_app.ask(rag_index, q["query"], top_k=5), what="ask")

    answer = _answer_text(res)
    assert answer.strip(), "ask() must return non-empty answer text"

    citations = _citations_from_ask(res)
    assert citations, "ask() must return citations in CI profile"

    contexts = _contexts_from_ask(res)
    assert contexts, "ask() must return the contexts it grounded on (contexts/candidates)"

    ctx_by_doc: dict[str, list[Any]] = {}
    for ctx in contexts:
        ctx_by_doc.setdefault(_doc_id(ctx), []).append(ctx)

    # At least one citation must cite an expected doc.
    cited_docs = {_doc_id(c) for c in citations}
    assert cited_docs & set(q["expected_doc_ids"]), (
        f"expected citations to include {q['expected_doc_ids']}; got={sorted(cited_docs)}"
    )

    # Every citation must map to a returned context and have a valid span.
    for cit in citations:
        did = _doc_id(cit)
        assert did in ctx_by_doc, f"citation doc_id={did} not in returned contexts"
        s, e = _span(cit)
        assert 0 <= s <= e, f"invalid citation span: {(s, e)}"

        # Span should fit within at least one context text for that doc.
        ok = False
        for ctx in ctx_by_doc[did]:
            t = _text(ctx)
            if not t:
                continue
            if e <= len(t):
                ok = True
                break
        assert ok, f"citation span {(s, e)} does not fit in any returned context for doc_id={did}"


@pytest.mark.e2e
@pytest.mark.parametrize("case", _CASE_PARAMS)
def test_ci_is_deterministic(
    rag_app: Any, rag_index: Any, rag_eval_suite: dict[str, Any], case: int
) -> None:
    """CI profile must be deterministic: same query -> identical outputs."""

    q = rag_eval_suite["queries"][case]
    query = q["query"]

    r1 = _unwrap_ok(rag_app.retrieve(rag_index, query, top_k=5), what="retrieve")
    r2 = _unwrap_ok(rag_app.retrieve(rag_index, query, top_k=5), what="retrieve")

    c1 = [_doc_id(c) for c in _candidates_from_retrieve(r1)]
    c2 = [_doc_id(c) for c in _candidates_from_retrieve(r2)]
    assert c1 == c2, "retrieve() must be deterministic in CI profile"

    a1 = _unwrap_ok(rag_app.ask(rag_index, query, top_k=5), what="ask")
    a2 = _unwrap_ok(rag_app.ask(rag_index, query, top_k=5), what="ask")

    assert _answer_text(a1) == _answer_text(a2), (
        "ask() answer text must be deterministic in CI profile"
    )

    cits1 = [(_doc_id(c), *_span(c)) for c in _citations_from_ask(a1)]
    cits2 = [(_doc_id(c), *_span(c)) for c in _citations_from_ask(a2)]
    assert cits1 == cits2, "ask() citations must be deterministic in CI profile"
