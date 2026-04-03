# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Tiny function-level rules DSL (Modules 02–03)."""

from __future__ import annotations

import ast
from typing import Any

from bijux_rag.core.rag_types import DocRule, RawDoc
from bijux_rag.core.rules_lint import SafeVisitor


def any_doc(_: RawDoc) -> bool:
    return True


def none_doc(_: RawDoc) -> bool:
    return False


def category_startswith(prefix: str) -> DocRule:
    def rule(doc: RawDoc) -> bool:
        return doc.categories.startswith(prefix)

    return rule


def title_contains(substr: str) -> DocRule:
    lowered = substr.lower()

    def rule(doc: RawDoc) -> bool:
        return lowered in doc.title.lower()

    return rule


def abstract_min_len(min_len: int) -> DocRule:
    def rule(doc: RawDoc) -> bool:
        return len(doc.abstract) >= min_len

    return rule


def rule_and(p: DocRule, q: DocRule) -> DocRule:
    def rule(doc: RawDoc) -> bool:
        return p(doc) and q(doc)

    return rule


def rule_or(p: DocRule, q: DocRule) -> DocRule:
    def rule(doc: RawDoc) -> bool:
        return p(doc) or q(doc)

    return rule


def rule_not(p: DocRule) -> DocRule:
    def rule(doc: RawDoc) -> bool:
        return not p(doc)

    return rule


def rule_all(*rules: DocRule) -> DocRule:
    def rule(doc: RawDoc) -> bool:
        return all(r(doc) for r in rules)

    return rule


def parse_rule(expr: str) -> DocRule:
    """Parse a safe boolean expression into a ``DocRule``.

    The expression is evaluated against a single bound name: ``d`` (the RawDoc).
    Example:
        d.categories.startswith("cs.") and len(d.abstract) > 500
    """

    tree = ast.parse(expr, mode="eval")
    SafeVisitor().visit(tree)

    def interpret(node: ast.AST, doc: RawDoc) -> Any:
        if isinstance(node, ast.Expression):
            return interpret(node.body, doc)
        if isinstance(node, ast.BoolOp):
            values = [interpret(v, doc) for v in node.values]
            if isinstance(node.op, ast.And):
                return all(values)
            if isinstance(node.op, ast.Or):
                return any(values)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return not interpret(node.operand, doc)
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and len(node.comparators) == 1:
            left = interpret(node.left, doc)
            right = interpret(node.comparators[0], doc)
            op = node.ops[0]
            if isinstance(op, ast.Gt):
                return left > right
            if isinstance(op, ast.GtE):
                return left >= right
            if isinstance(op, ast.Lt):
                return left < right
            if isinstance(op, ast.LtE):
                return left <= right
            if isinstance(op, ast.Eq):
                return left == right
            if isinstance(op, ast.NotEq):
                return left != right
            if isinstance(op, ast.In):
                return left in right
            if isinstance(op, ast.NotIn):
                return left not in right
            raise ValueError(f"Unsupported compare op: {type(op).__name__}")
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "d"
        ):
            if node.attr == "title":
                return doc.title
            if node.attr == "abstract":
                return doc.abstract
            if node.attr == "categories":
                return doc.categories
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "len":
            return len(interpret(node.args[0], doc))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            base_value = interpret(node.func.value, doc)
            arg_value = interpret(node.args[0], doc) if node.args else None
            if node.func.attr == "lower":
                if not isinstance(base_value, str):
                    raise ValueError("lower() base must be str")
                return base_value.lower()
            if node.func.attr == "startswith":
                if not isinstance(base_value, str) or not isinstance(arg_value, str):
                    raise ValueError("startswith() requires (str, str)")
                return base_value.startswith(arg_value)
        if isinstance(node, ast.Constant):
            return node.value
        raise ValueError(f"Unsupported expression node: {type(node).__name__}")

    def rule(doc: RawDoc) -> bool:
        return bool(interpret(tree, doc))

    return rule


__all__ = [
    "any_doc",
    "none_doc",
    "category_startswith",
    "title_contains",
    "abstract_min_len",
    "rule_and",
    "rule_or",
    "rule_not",
    "rule_all",
    "parse_rule",
]
