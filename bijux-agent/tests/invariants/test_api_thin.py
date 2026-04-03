"""Invariant: API layer stays thin."""

from __future__ import annotations

import ast
from pathlib import Path

MAX_AVG_COMPLEXITY = 6.0
MAX_LOC = 200


def _function_complexity(node: ast.AST) -> int:
    complexity = 1
    for child in ast.walk(node):
        if isinstance(
            child,
            (
                ast.If,
                ast.For,
                ast.AsyncFor,
                ast.While,
                ast.Try,
                ast.With,
                ast.AsyncWith,
                ast.BoolOp,
                ast.Match,
            ),
        ):
            complexity += 1
    return complexity


def test_api_v1_stays_small() -> None:
    api_v1 = Path(__file__).resolve().parents[2] / "src" / "bijux_agent" / "api" / "v1"
    complexities: list[int] = []
    for path in api_v1.glob("*.py"):
        lines = path.read_text(encoding="utf-8").splitlines()
        assert len(lines) <= MAX_LOC, f"{path} exceeds {MAX_LOC} lines"
        tree = ast.parse("\n".join(lines), filename=str(path))
        complexities.extend(
            [
                _function_complexity(node)
                for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]
        )
    average = sum(complexities) / len(complexities) if complexities else 0.0
    assert average < MAX_AVG_COMPLEXITY, f"API complexity too high: {average:.2f}"
