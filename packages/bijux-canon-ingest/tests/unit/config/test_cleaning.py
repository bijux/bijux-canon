# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from bijux_canon_ingest.config.cleaning import (
    CleanConfig,
    clean_abstract,
    collapse_ws,
    make_cleaner,
    replace_newlines,
)
from bijux_canon_ingest.core.types import RawDoc
import pytest


def test_text_rules_normalize_whitespace_and_newlines() -> None:
    assert collapse_ws("a   b\t c") == "a b c"
    assert replace_newlines("a\nb\nc") == "a b c"


def test_clean_abstract_applies_rules_in_declared_order() -> None:
    config = CleanConfig(rule_names=("replace_newlines", "collapse_ws", "upper"))
    assert clean_abstract("  hello\nworld  ", config) == "HELLO WORLD"


def test_make_cleaner_only_changes_abstract() -> None:
    cleaner = make_cleaner(CleanConfig(rule_names=("strip", "lower")))
    doc = RawDoc(
        doc_id="d1",
        title="Title",
        abstract="  Hello World  ",
        categories="cs.AI",
    )

    cleaned = cleaner(doc)

    assert cleaned.doc_id == doc.doc_id
    assert cleaned.title == doc.title
    assert cleaned.categories == doc.categories
    assert cleaned.abstract == "hello world"


def test_clean_abstract_rejects_unknown_rule_name() -> None:
    with pytest.raises(KeyError):
        clean_abstract("hello", CleanConfig(rule_names=("missing",)))
