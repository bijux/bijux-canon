# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Application services and orchestration for ``bijux-canon-ingest``.

This package exposes orchestration entrypoints without importing every adapter
and optional workflow helper at module import time.
"""

from __future__ import annotations

from typing import Any

from bijux_canon_ingest._lazy_exports import LazyExport, resolve_lazy_export

_LAZY_EXPORTS: dict[str, LazyExport] = {
    "CanonicalIngestError": (".canonical_ingest", "CanonicalIngestError"),
    "CanonicalIngestRequest": (".canonical_ingest", "CanonicalIngestRequest"),
    "CanonicalIngestResult": (".canonical_ingest", "CanonicalIngestResult"),
    "CanonicalIngestRuntime": (".canonical_ingest", "CanonicalIngestRuntime"),
    "apply_corpus_delta": (".corpus_delta", "apply_corpus_delta"),
    "assess_ocr_requirement": (".document_extraction", "assess_ocr_requirement"),
    "DebugConfig": ("bijux_canon_ingest.observability", "DebugConfig"),
    "ErrorPolicy": (".pipeline_definitions", "ErrorPolicy"),
    "IndexBackend": (".service", "IndexBackend"),
    "IndexBuildConfig": (".indexing", "IndexBuildConfig"),
    "IngestService": (".service", "IngestService"),
    "IngestTaps": ("bijux_canon_ingest.observability", "IngestTaps"),
    "IngestTrace": ("bijux_canon_ingest.observability", "IngestTrace"),
    "Observations": ("bijux_canon_ingest.observability", "Observations"),
    "OperatorSpec": (".pipeline_definitions", "OperatorSpec"),
    "PipelineConfig": (".pipeline_definitions", "PipelineConfig"),
    "PipelineSpec": (".pipeline_definitions", "PipelineSpec"),
    "SpecRegistry": (".pipeline_definitions", "SpecRegistry"),
    "StepConfig": (".pipeline_definitions", "StepConfig"),
    "StoredIndex": (".service", "StoredIndex"),
    "TraceLens": ("bijux_canon_ingest.observability", "TraceLens"),
    "ask": (".querying", "ask"),
    "beam_available": (".pipeline_definitions", "beam_available"),
    "build_chunk_span_mapping": (".source_mapping", "build_chunk_span_mapping"),
    "build_corpus_snapshot": (".corpus_snapshot", "build_corpus_snapshot"),
    "build_document_span_mappings": (
        ".source_mapping",
        "build_document_span_mappings",
    ),
    "build_index_from_docs": (".indexing", "build_index_from_docs"),
    "build_rag_pipeline": (".pipeline_definitions", "build_rag_pipeline"),
    "canonical_json": (".pipeline_definitions", "canonical_json"),
    "chunk_document_mappings": (
        ".semantic_chunking",
        "chunk_document_mappings",
    ),
    "compile_to_beam": (".pipeline_definitions", "compile_to_beam"),
    "compile_to_dask_bag": (".pipeline_definitions", "compile_to_dask_bag"),
    "dask_available": (".pipeline_definitions", "dask_available"),
    "discover_sources": (".source_discovery", "discover_sources"),
    "normalize_source_metadata": (".source_metadata", "normalize_source_metadata"),
    "parse_docx": (".document_extraction", "parse_docx"),
    "parse_html": (".document_extraction", "parse_html"),
    "parse_jats": (".document_extraction", "parse_jats"),
    "parse_markdown": (".document_extraction", "parse_markdown"),
    "parse_pdf": (".document_extraction", "parse_pdf"),
    "parse_text": (".document_extraction", "parse_text"),
    "ingest_docs_to_chunks": (".indexing", "ingest_docs_to_chunks"),
    "iter_chunks_from_cleaned": (".pipeline", "iter_chunks_from_cleaned"),
    "iter_ingest_pipeline": (".pipeline", "iter_ingest_pipeline"),
    "ingest_corpus": (".canonical_ingest", "ingest_corpus"),
    "iter_ingest_pipeline_core": (".pipeline", "iter_ingest_pipeline_core"),
    "parse_filters": (".querying", "parse_filters"),
    "plan_corpus_delta": (".corpus_delta", "plan_corpus_delta"),
    "publish_corpus_snapshot": (".corpus_publication", "publish_corpus_snapshot"),
    "read_published_corpus_snapshot": (
        ".corpus_publication",
        "read_published_corpus_snapshot",
    ),
    "recover_corpus_snapshot_store": (
        ".corpus_publication",
        "recover_corpus_snapshot_store",
    ),
    "reconstruct_pipeline": (".pipeline_definitions", "reconstruct_pipeline"),
    "retrieve": (".querying", "retrieve"),
    "run_ingest_pipeline": (".pipeline", "run_ingest_pipeline"),
    "run_ingest_pipeline_docs": (".pipeline", "run_ingest_pipeline_docs"),
    "run_ingest_pipeline_path": (".pipeline", "run_ingest_pipeline_path"),
    "spec_hash": (".pipeline_definitions", "spec_hash"),
}

__all__ = [
    "CanonicalIngestError",
    "CanonicalIngestRequest",
    "CanonicalIngestResult",
    "CanonicalIngestRuntime",
    "apply_corpus_delta",
    "assess_ocr_requirement",
    "iter_ingest_pipeline",
    "ingest_corpus",
    "iter_ingest_pipeline_core",
    "iter_chunks_from_cleaned",
    "run_ingest_pipeline",
    "run_ingest_pipeline_docs",
    "run_ingest_pipeline_path",
    "DebugConfig",
    "IngestTaps",
    "Observations",
    "TraceLens",
    "IngestTrace",
    "IndexBuildConfig",
    "IndexBackend",
    "StoredIndex",
    "IngestService",
    "ingest_docs_to_chunks",
    "build_chunk_span_mapping",
    "build_corpus_snapshot",
    "build_document_span_mappings",
    "chunk_document_mappings",
    "build_index_from_docs",
    "retrieve",
    "ask",
    "parse_filters",
    "plan_corpus_delta",
    "publish_corpus_snapshot",
    "read_published_corpus_snapshot",
    "recover_corpus_snapshot_store",
    "StepConfig",
    "PipelineConfig",
    "build_rag_pipeline",
    "dask_available",
    "beam_available",
    "compile_to_dask_bag",
    "compile_to_beam",
    "ErrorPolicy",
    "OperatorSpec",
    "PipelineSpec",
    "SpecRegistry",
    "canonical_json",
    "spec_hash",
    "reconstruct_pipeline",
    "discover_sources",
    "normalize_source_metadata",
    "parse_docx",
    "parse_html",
    "parse_jats",
    "parse_markdown",
    "parse_pdf",
    "parse_text",
]


def __getattr__(name: str) -> Any:
    value = resolve_lazy_export(
        module_name=__name__,
        name=name,
        exports=_LAZY_EXPORTS,
    )
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__) | set(_LAZY_EXPORTS))
