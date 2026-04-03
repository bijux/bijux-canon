# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
"""
Deterministic extractive reasoning utilities with verifiable citations.

SPDX-FileCopyrightText: © 2025 Bijan Mousavi
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re

from bijux_rar.rar.retrieval.bm25 import tokenize

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class Citation:
    evidence_id: str
    span: tuple[int, int]
    snippet_sha256: str


@dataclass(frozen=True)
class Derivation:
    """Structured derivation output."""

    statement: str
    citations: list[Citation]
    raw_reasoner: dict[str, object] | None = None
    result_sha256: str | None = None


def _char_to_byte_offsets(text: str) -> list[int]:
    """Map character indices to UTF-8 byte offsets."""
    offsets = [0]
    total = 0
    for ch in text:
        total += len(ch.encode("utf-8"))
        offsets.append(total)
    return offsets


def _split_sentences(text: str) -> list[tuple[str, int, int]]:
    """Return (sentence, char_start, char_end) in original text."""
    text = text.strip()
    if not text:
        return []
    out: list[tuple[str, int, int]] = []
    start = 0
    for m in _SENT_SPLIT.finditer(text):
        end = m.start()
        seg = text[start:end].strip()
        if seg:
            out.append((seg, start, end))
        start = m.end()
    if start < len(text):
        seg = text[start:].strip()
        if seg:
            out.append((seg, start, len(text)))
    return out


def derive_extractive_answer(
    *,
    question: str,
    evidence: list[tuple[str, bytes]],
    max_citations: int = 2,
) -> Derivation:
    """Produce a deterministic statement with verifiable citation markers.

    Markers follow: [evidence:<id>:<b0>-<b1>:<sha256>]
    where span is over the UTF-8 evidence bytes.
    """
    if not evidence:
        return Derivation(
            statement="No evidence retrieved.",
            citations=[],
            raw_reasoner={"reason": "no_evidence"},
            result_sha256=None,
        )

    q_tokens = set(tokenize(question))
    candidates: list[tuple[int, str, str, tuple[int, int], str]] = []
    # (score, sentence, evidence_id, span_bytes, sha256)

    for eid, ev_bytes in evidence:
        try:
            text = ev_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = ev_bytes.decode("utf-8", errors="replace")

        offsets = _char_to_byte_offsets(text)
        best: tuple[int, str, tuple[int, int], str] | None = None

        for sent, c0, c1 in _split_sentences(text):
            s_tokens = set(tokenize(sent))
            score = len(q_tokens & s_tokens)
            b0 = offsets[c0]
            b1 = offsets[c1]
            if b1 <= b0:
                continue
            snippet = ev_bytes[b0:b1]
            sha = hashlib.sha256(snippet).hexdigest()
            cand = (score, sent, (b0, b1), sha)
            if (
                best is None
                or cand[0] > best[0]
                or (cand[0] == best[0] and (cand[1] < best[1] or cand[2] < best[2]))
            ):
                best = cand

        if best is None:
            # Fallback: cite a deterministic prefix.
            prefix = text.replace("\n", " ").strip()
            prefix = prefix[:200].rstrip() + ("..." if len(prefix) > 200 else "")
            b0, b1 = 0, len(prefix.encode("utf-8"))
            sha = hashlib.sha256(ev_bytes[b0:b1]).hexdigest()
            best = (0, prefix, (b0, b1), sha)

        score, sent, span_b, sha = best
        candidates.append((score, sent, eid, span_b, sha))

    # Pick top-N candidates deterministically by score then sentence then eid.
    candidates.sort(key=lambda t: (-t[0], t[1], t[2], t[3]))
    max_citations = max(1, int(max_citations))
    chosen = candidates[:max_citations]

    citations: list[Citation] = []
    parts: list[str] = []
    for score, sent, eid, (b0, b1), sha in chosen:
        _ = score
        citations.append(Citation(evidence_id=eid, span=(b0, b1), snippet_sha256=sha))
        parts.append(f"{sent} [evidence:{eid}:{b0}-{b1}:{sha}]")

    statement = " ".join(parts).strip()
    raw: dict[str, object] = {
        "reasoner": "baseline_extractive_v2",
        "question": question,
        "picked": [
            {
                "evidence_id": c.evidence_id,
                "span": list(c.span),
                "sha": c.snippet_sha256,
            }
            for c in citations
        ],
    }
    result_hash = hashlib.sha256(
        statement.encode("utf-8")
        + b"|"
        + b";".join(
            f"{c.evidence_id}:{c.span[0]}-{c.span[1]}:{c.snippet_sha256}".encode()
            for c in citations
        )
    ).hexdigest()
    return Derivation(
        statement=statement,
        citations=citations,
        raw_reasoner=raw,
        result_sha256=result_hash,
    )
