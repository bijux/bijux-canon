# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Configuration-as-data for deterministic document cleaning (Modules 02–05).

This is introduced in Bijux RAG and kept stable through Bijux RAG: represent
cleaning as immutable data and bind it into a pure ``RawDoc -> CleanDoc`` stage.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from bijux_rag.core.rag_types import CleanDoc, RawDoc

TextRule = Callable[[str], str]


def collapse_ws(text: str) -> str:
    return " ".join(text.split())


def replace_newlines(text: str) -> str:
    return text.replace("\n", " ")


RULES: dict[str, TextRule] = {
    "strip": str.strip,
    "lower": str.lower,
    "upper": str.upper,
    "collapse_ws": collapse_ws,
    "replace_newlines": replace_newlines,
}


@dataclass(frozen=True)
class CleanConfig:
    """Immutable cleaning configuration expressed as rule names."""

    rule_names: tuple[str, ...] = ("strip", "lower", "collapse_ws")


DEFAULT_CLEAN_CONFIG = CleanConfig()


def clean_abstract(text: str, cfg: CleanConfig) -> str:
    for name in cfg.rule_names:
        rule = RULES[name]
        text = rule(text)
    return text


def make_cleaner(cfg: CleanConfig) -> Callable[[RawDoc], CleanDoc]:
    """Bind a cleaner config into a pure ``RawDoc -> CleanDoc``."""

    def cleaner(doc: RawDoc) -> CleanDoc:
        abstract = clean_abstract(doc.abstract, cfg)
        return CleanDoc(
            doc_id=doc.doc_id, title=doc.title, abstract=abstract, categories=doc.categories
        )

    return cleaner


__all__ = [
    "TextRule",
    "CleanConfig",
    "DEFAULT_CLEAN_CONFIG",
    "RULES",
    "collapse_ws",
    "replace_newlines",
    "clean_abstract",
    "make_cleaner",
]
