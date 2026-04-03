from __future__ import annotations

import inspect

from bijux_canon_agent.examples import document_review, minimal


def test_example_exports_are_coroutines() -> None:
    assert inspect.iscoroutinefunction(minimal.run_minimal)
    assert inspect.iscoroutinefunction(document_review.run_document_review)
