# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Answer generation backends.

For CI and deterministic evaluation, bijux-rag ships an extractive generator.
It assembles an answer from retrieved evidence spans and always emits citations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from bijux_rag.rag.ports import Answer, Candidate, Citation


@dataclass(frozen=True, slots=True)
class ExtractiveGenerator:
    """Deterministic, citation-only generator.

    This generator **never** invents information. It only selects snippets from
    retrieved chunks. That makes it stable for CI baselines.

    Args:
        max_chars: Max chars to include in the answer.
        min_score: Minimum candidate score to consider.
    """

    max_chars: int = 800
    min_score: float = 0.0

    def generate(self, *, query: str, candidates: Sequence[Candidate]) -> Answer:
        # Filter by score and take evidence in rank order.
        evidence = [c for c in candidates if float(c.score) >= self.min_score]
        if not evidence:
            return Answer(
                text="Cannot answer from sources.", citations=(), candidates=tuple(candidates)
            )

        parts: list[str] = []
        cites: list[Citation] = []
        used = 0
        for c in evidence:
            if used >= self.max_chars:
                break
            txt = c.chunk.text.strip()
            if not txt:
                continue
            take = txt[: max(0, self.max_chars - used)]
            if take:
                parts.append(take)
                used += len(take)
                cites.append(
                    Citation(
                        doc_id=c.chunk.doc_id,
                        chunk_id=c.chunk.chunk_id,
                        start=c.chunk.start,
                        end=c.chunk.end,
                    )
                )
        text = "\n\n".join(parts).strip() if parts else "Cannot answer from sources."
        return Answer(text=text, citations=tuple(cites), candidates=tuple(candidates))


__all__ = ["ExtractiveGenerator"]
