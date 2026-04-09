# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from bijux_canon_ingest.core.rules_dsl import (
    abstract_min_len,
    category_startswith,
    parse_rule,
    rule_all,
    rule_not,
    title_contains,
)
from bijux_canon_ingest.core.rules_lint import assert_rule_is_safe_expr
from bijux_canon_ingest.core.structural_dedup import structural_dedup_lazy
from bijux_canon_ingest.core.types import Chunk, RawDoc
from bijux_canon_ingest.result import Ok
import pytest


def test_parse_rule_supports_safe_doc_expressions() -> None:
    doc = RawDoc("d1", "Deterministic Systems", "Reliable pipelines", "cs.SE")
    rule = parse_rule(
        'd.categories.startswith("cs.") and len(d.abstract) >= 8 and "systems" in d.title.lower()'
    )

    assert rule(doc)


def test_rule_lint_rejects_unsupported_calls() -> None:
    with pytest.raises(ValueError, match="Forbidden"):
        assert_rule_is_safe_expr('__import__("os").system("pwd")')


def test_rule_combinators_compose_predicates() -> None:
    doc = RawDoc("d1", "Safe Systems", "clear and precise", "cs.SE")
    keep = rule_all(
        category_startswith("cs."),
        title_contains("systems"),
        abstract_min_len(10),
        rule_not(title_contains("draft")),
    )

    assert keep(doc)


def test_structural_dedup_lazy_preserves_first_seen_chunk() -> None:
    first = Chunk.create(
        doc_id="d1",
        chunk_index=0,
        start=0,
        end=4,
        text="text",
        title="Title",
        category="cs.SE",
        metadata={"source": "first"},
    )
    duplicate = Chunk.create(
        doc_id="d1",
        chunk_index=1,
        start=0,
        end=4,
        text="text",
        title="Title",
        category="cs.SE",
        metadata={"source": "duplicate"},
    )
    later = Chunk.create(
        doc_id="d2",
        chunk_index=0,
        start=0,
        end=5,
        text="later",
        title="Other",
        category="math.NT",
    )

    assert isinstance(first, Ok)
    assert isinstance(duplicate, Ok)
    assert isinstance(later, Ok)

    chunks = list(
        structural_dedup_lazy([first.value, duplicate.value, later.value, first.value])
    )

    assert chunks == [first.value, later.value]
    assert chunks[0].metadata["source"] == "first"
