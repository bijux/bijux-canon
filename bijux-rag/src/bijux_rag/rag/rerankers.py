# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Reference rerankers.

The default reranker is deterministic and CI-friendly: lexical overlap.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from bijux_rag.rag.indexes import _tokenize
from bijux_rag.rag.ports import Candidate


@dataclass(frozen=True, slots=True)
class LexicalOverlapReranker:
    """Rerank by token overlap ratio.

    This is a cheap, deterministic reranker that improves lexical baselines.
    """

    def rerank(self, *, query: str, candidates: Sequence[Candidate], top_k: int) -> list[Candidate]:
        def _stem(tok: str) -> str:
            if tok.endswith("es") and len(tok) > 4:
                return tok[:-1]  # combines -> combine, passages -> passage
            if tok.endswith("s") and len(tok) > 3:
                return tok[:-1]
            return tok

        qtoks = {_stem(t) for t in _tokenize(query)}
        if not qtoks:
            return list(candidates)[: max(0, int(top_k))]

        scored: list[tuple[float, Candidate]] = []
        for c in candidates:
            ctoks = {_stem(t) for t in _tokenize(c.chunk.text)}
            inter = len(qtoks & ctoks)
            denom = max(1, len(qtoks))
            boost = inter / denom
            scored.append((float(c.score) + boost, c))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored[: max(0, int(top_k))]]


__all__ = ["LexicalOverlapReranker"]
