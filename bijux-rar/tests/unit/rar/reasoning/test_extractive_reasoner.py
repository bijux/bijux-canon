# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

import hashlib

from bijux_rar.rar.reasoning.extractive import derive_extractive_answer


def test_extractive_reasoner_emits_citations_with_span_and_hash() -> None:
    ev_bytes = b"Rust is a systems language. It focuses on safety and speed."
    deriv = derive_extractive_answer(
        question="What is Rust focused on?",
        evidence=[("e1", ev_bytes)],
        max_citations=1,
    )

    assert deriv.citations
    citation = deriv.citations[0]
    assert citation.evidence_id == "e1"
    b0, b1 = citation.span
    assert 0 <= b0 < b1 <= len(ev_bytes)
    expected_sha = hashlib.sha256(ev_bytes[b0:b1]).hexdigest()
    assert citation.snippet_sha256 == expected_sha
    marker = f"[evidence:e1:{b0}-{b1}:{expected_sha}]"
    assert marker in deriv.statement


def test_extractive_reasoner_is_deterministic_with_multiple_evidence() -> None:
    ev1 = ("e1", b"Alpha beta gamma.")
    ev2 = ("e2", b"Gamma beta alpha.")
    deriv_a = derive_extractive_answer(
        question="beta alpha",
        evidence=[ev1, ev2],
        max_citations=2,
    )
    deriv_b = derive_extractive_answer(
        question="beta alpha",
        evidence=[ev1, ev2],
        max_citations=2,
    )

    assert deriv_a.citations == deriv_b.citations
    assert deriv_a.statement == deriv_b.statement


def test_extractive_reasoner_handles_no_evidence() -> None:
    deriv = derive_extractive_answer(
        question="anything", evidence=[], max_citations=2
    )
    assert deriv.citations == []
    assert "No evidence retrieved" in deriv.statement
    assert deriv.raw_reasoner and deriv.raw_reasoner.get("reason") == "no_evidence"
    assert deriv.result_sha256 is None


def test_extractive_reasoner_replaces_invalid_utf() -> None:
    ev_bytes = b"\xff\xfe\xfd"  # invalid UTF-8
    deriv = derive_extractive_answer(
        question="q", evidence=[("bad", ev_bytes)], max_citations=1
    )
    # Even with invalid bytes, should produce a citation with valid bounds/hash
    assert deriv.citations
    c = deriv.citations[0]
    assert c.span[0] >= 0 and c.span[1] > c.span[0]
    expected_sha = hashlib.sha256(ev_bytes[c.span[0] : c.span[1]]).hexdigest()
    assert c.snippet_sha256 == expected_sha
