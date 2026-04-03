# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

import pytest

from time import perf_counter

from bijux_rar.rar.retrieval.bm25 import BM25Index
from bijux_rar.rar.retrieval.corpus import CorpusDoc


@pytest.mark.benchmark(group="retrieval")
def test_bm25_topk_benchmark(benchmark: pytest.BenchmarkFixture) -> None:
    docs = [
        CorpusDoc(doc_id=f"d{i}", text="hello world " * 5, title=None, source=None)
        for i in range(200)
    ]
    idx = BM25Index.build(docs)

    def _run_many(iterations: int) -> float:
        start = perf_counter()
        for _ in range(iterations):
            idx.top_k("hello", k=5)
        return perf_counter() - start

    # Warm up once to avoid cold-start artifacts
    _run_many(10)

    duration = benchmark(lambda: _run_many(50))
    # Assert the per-call average stays under a generous threshold to catch regressions.
    per_call_ms = (duration / 50) * 1000.0
    assert per_call_ms < 5.0, f"BM25 top_k regression: {per_call_ms:.3f} ms/call"
