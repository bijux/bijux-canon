from __future__ import annotations

import inspect

from bijux_canon_agent.tooling.example_pipelines import document_review, minimal


def test_example_pipeline_exports_are_coroutines() -> None:
    assert inspect.iscoroutinefunction(minimal.run_minimal)
    assert inspect.iscoroutinefunction(document_review.run_document_review)
