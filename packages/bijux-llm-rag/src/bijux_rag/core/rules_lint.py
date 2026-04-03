# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""AST validator for dynamic rule expressions (Modules 02–03)."""

from __future__ import annotations

import ast


class SafeVisitor(ast.NodeVisitor):
    """Whitelist-driven visitor ensuring expressions stay within a small sandbox."""

    _ALLOWED_NODES = (
        ast.Expression,
        ast.BoolOp,
        ast.UnaryOp,
        ast.Compare,
        ast.Call,
        ast.Attribute,
        ast.Name,
        ast.Load,
        ast.Constant,
        ast.And,
        ast.Or,
        ast.Gt,
        ast.GtE,
        ast.Lt,
        ast.LtE,
        ast.Eq,
        ast.NotEq,
        ast.In,
        ast.NotIn,
        ast.Not,
    )
    _ALLOWED_BOOL_OPS = (ast.And, ast.Or)
    _ALLOWED_UNARY_OPS = (ast.Not,)
    _ALLOWED_CALL_NAMES = {"len"}
    _ALLOWED_ATTRIBUTE_CALLS = {"startswith", "lower"}

    def generic_visit(self, node: ast.AST) -> None:  # pragma: no cover
        if not isinstance(node, self._ALLOWED_NODES):
            raise ValueError(f"Forbidden node type: {type(node).__name__}")
        super().generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        if not isinstance(node.op, self._ALLOWED_BOOL_OPS):
            raise ValueError(f"Forbidden boolean op: {type(node.op).__name__}")
        self.generic_visit(node)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> None:
        if not isinstance(node.op, self._ALLOWED_UNARY_OPS):
            raise ValueError(f"Forbidden unary op: {type(node.op).__name__}")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name):
            if node.func.id not in self._ALLOWED_CALL_NAMES:
                raise ValueError(f"Forbidden call: {node.func.id}")
        elif isinstance(node.func, ast.Attribute):
            if node.func.attr not in self._ALLOWED_ATTRIBUTE_CALLS:
                raise ValueError(f"Forbidden attribute call: {node.func.attr}")
        else:
            raise ValueError("Only simple function calls are allowed")
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        allowed_names = {"d", *self._ALLOWED_CALL_NAMES}
        if node.id not in allowed_names:
            raise ValueError(f"Forbidden name: {node.id}")

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if not self._attr_chain_from_doc(node):
            raise ValueError("Attributes must be accessed off 'd'")
        allowed_attrs = {"title", "abstract", "categories", *self._ALLOWED_ATTRIBUTE_CALLS}
        if node.attr not in allowed_attrs:
            raise ValueError(f"Unsupported attribute: {node.attr}")
        self.generic_visit(node)

    @staticmethod
    def _attr_chain_from_doc(node: ast.AST) -> bool:
        current: ast.AST = node
        while isinstance(current, ast.Attribute):
            current = current.value
        return isinstance(current, ast.Name) and current.id == "d"


def assert_rule_is_safe_expr(expr: str) -> None:
    tree = ast.parse(expr, mode="eval")
    SafeVisitor().visit(tree)


__all__ = ["SafeVisitor", "assert_rule_is_safe_expr"]
