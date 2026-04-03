# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""A tiny, frozen predicate DSL expressed as data (Modules 02–03)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Union

from bijux_rag.core.rag_types import RawDoc


@dataclass(frozen=True)
class Eq:
    path: str
    value: Any


@dataclass(frozen=True)
class StartsWith:
    path: str
    value: str


@dataclass(frozen=True)
class LenGt:
    path: str
    value: int


@dataclass(frozen=True)
class All:
    rules: tuple["Pred", ...]


@dataclass(frozen=True)
class AnyOf:
    rules: tuple["Pred", ...]


@dataclass(frozen=True)
class Not:
    rule: "Pred"


Pred = Union[Eq, StartsWith, LenGt, All, AnyOf, Not]


@dataclass(frozen=True)
class RulesConfig:
    keep_pred: Pred = All(())


DEFAULT_RULES = RulesConfig()


def _get_path(doc: RawDoc, path: str) -> Any:
    if path == "doc_id":
        return doc.doc_id
    if path == "title":
        return doc.title
    if path == "abstract":
        return doc.abstract
    if path == "categories":
        return doc.categories
    raise ValueError(f"Unknown path: {path!r}")


def eval_pred(doc: RawDoc, pred: Pred) -> bool:
    if isinstance(pred, Eq):
        return bool(_get_path(doc, pred.path) == pred.value)
    if isinstance(pred, StartsWith):
        value = _get_path(doc, pred.path)
        if not isinstance(value, str):
            raise ValueError(f"StartsWith path must be str, got {type(value).__name__}")
        return value.startswith(pred.value)
    if isinstance(pred, LenGt):
        value = _get_path(doc, pred.path)
        if not isinstance(value, (str, tuple, list)):
            raise ValueError(f"LenGt path must be sized, got {type(value).__name__}")
        return len(value) > pred.value
    if isinstance(pred, All):
        return all(eval_pred(doc, p) for p in pred.rules)
    if isinstance(pred, AnyOf):
        return any(eval_pred(doc, p) for p in pred.rules)
    if isinstance(pred, Not):
        return not eval_pred(doc, pred.rule)
    raise ValueError(f"Unknown predicate: {type(pred).__name__}")


__all__ = [
    "Pred",
    "Eq",
    "StartsWith",
    "LenGt",
    "All",
    "AnyOf",
    "Not",
    "RulesConfig",
    "DEFAULT_RULES",
    "eval_pred",
]
