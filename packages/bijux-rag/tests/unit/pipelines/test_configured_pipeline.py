# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from bijux_rag.core.rag_types import RawDoc
from bijux_rag.pipelines.configured import PipelineConfig, StepConfig, build_rag_pipeline
from bijux_rag.result.types import is_ok


def test_build_rag_pipeline_happy_path() -> None:
    cfg = PipelineConfig(
        steps=(
            StepConfig("clean"),
            StepConfig("chunk", {"chunk_size": 8}),
            StepConfig("embed"),
        )
    )

    pipeline = build_rag_pipeline(cfg)
    docs = iter([RawDoc(doc_id="d1", title="t", abstract="hello world", categories="cs.AI")])
    out = list(pipeline(docs))
    assert out
    assert all(is_ok(r) for r in out)


def test_build_rag_pipeline_rejects_bad_order() -> None:
    cfg = PipelineConfig(steps=(StepConfig("embed"),))
    try:
        _ = build_rag_pipeline(cfg)
    except TypeError:
        return
    raise AssertionError("expected TypeError")


def test_build_rag_pipeline_reports_embed_exceptions() -> None:
    cfg = PipelineConfig(
        steps=(
            StepConfig("clean"),
            StepConfig("chunk", {"chunk_size": 4}),
            StepConfig("embed"),
        )
    )

    def bad_embedder(_x):
        raise RuntimeError("boom")

    pipeline = build_rag_pipeline(cfg, artifacts={"embed": {"embedder": bad_embedder}})
    docs = iter([RawDoc(doc_id="d1", title="t", abstract="hello", categories="cs.AI")])
    out = list(pipeline(docs))
    assert out and not all(is_ok(r) for r in out)
    assert any((not is_ok(r) and r.error.code == "UNEXPECTED") for r in out)
