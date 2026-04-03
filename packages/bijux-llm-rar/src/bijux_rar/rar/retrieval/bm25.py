# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
"""
Deterministic BM25 implementation.

SPDX-FileCopyrightText: © 2025 Bijan Mousavi
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
import math
import re

from bijux_rar.rar.retrieval.corpus import CorpusDoc

# Locale-independent tokenizer to avoid locale drift.
_WORD_RE = re.compile(r"[A-Za-z0-9_]+", flags=re.ASCII)


def tokenize(text: str) -> list[str]:
    """Deterministic tokenization used by the built-in retriever."""
    return [m.group(0).lower() for m in _WORD_RE.finditer(text)]


@dataclass(frozen=True)
class BM25Index:
    docs: tuple[CorpusDoc, ...]
    doc_tokens: tuple[tuple[str, ...], ...]
    doc_tf: tuple[Counter[str], ...]
    df: Counter[str]
    avgdl: float

    @staticmethod
    def build(docs: Iterable[CorpusDoc]) -> BM25Index:
        dlist = tuple(docs)
        if not dlist:
            raise ValueError("Cannot build BM25Index for empty corpus")
        toks: list[tuple[str, ...]] = []
        tfs: list[Counter[str]] = []
        df: Counter[str] = Counter()
        total_len = 0
        for d in dlist:
            tt = tuple(tokenize(d.text))
            toks.append(tt)
            tf = Counter(tt)
            tfs.append(tf)
            total_len += len(tt)
            for term in tf:
                df[term] += 1
        avgdl = total_len / float(len(dlist))
        return BM25Index(
            docs=dlist,
            doc_tokens=tuple(toks),
            doc_tf=tuple(tfs),
            df=df,
            avgdl=avgdl,
        )

    def score(
        self, query_tokens: list[str], *, k1: float = 1.2, b: float = 0.75
    ) -> list[float]:
        doc_count = len(self.docs)
        scores = [0.0 for _ in range(doc_count)]
        q_terms = Counter(query_tokens)
        for i in range(doc_count):
            dl = len(self.doc_tokens[i])
            tf = self.doc_tf[i]
            denom_norm = k1 * (1.0 - b + b * (dl / self.avgdl))
            s = 0.0
            for term, qf in q_terms.items():
                n = self.df.get(term, 0)
                if n == 0:
                    continue
                idf = math.log(1.0 + (doc_count - n + 0.5) / (n + 0.5))
                f = tf.get(term, 0)
                if f == 0:
                    continue
                s += idf * ((f * (k1 + 1.0)) / (f + denom_norm)) * float(qf)
            scores[i] = round(s, 6)
        return scores

    def top_k(
        self, query: str, *, k: int = 3, k1: float = 1.2, b: float = 0.75
    ) -> list[tuple[CorpusDoc, float]]:
        qt = tokenize(query)
        scores = self.score(qt, k1=k1, b=b)
        ranked = sorted(
            ((self.docs[i], scores[i]) for i in range(len(self.docs))),
            key=lambda x: (-round(x[1], 6), x[0].doc_id),
        )
        return ranked[: max(0, int(k))]
