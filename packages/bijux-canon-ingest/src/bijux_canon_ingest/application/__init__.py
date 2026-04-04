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
    "build_index_from_csv": (".indexing", "build_index_from_csv"),
    "build_rag_pipeline": (".pipeline_definitions", "build_rag_pipeline"),
    "canonical_json": (".pipeline_definitions", "canonical_json"),
    "compile_to_beam": (".pipeline_definitions", "compile_to_beam"),
    "compile_to_dask_bag": (".pipeline_definitions", "compile_to_dask_bag"),
    "dask_available": (".pipeline_definitions", "dask_available"),
    "ingest_csv_to_chunks": (".indexing", "ingest_csv_to_chunks"),
    "ingest_docs_to_chunks": (".indexing", "ingest_docs_to_chunks"),
    "iter_chunks_from_cleaned": (".pipeline", "iter_chunks_from_cleaned"),
    "iter_ingest_pipeline": (".pipeline", "iter_ingest_pipeline"),
    "iter_ingest_pipeline_core": (".pipeline", "iter_ingest_pipeline_core"),
    "parse_filters": (".querying", "parse_filters"),
    "reconstruct_pipeline": (".pipeline_definitions", "reconstruct_pipeline"),
    "retrieve": (".querying", "retrieve"),
    "run_ingest_pipeline": (".pipeline", "run_ingest_pipeline"),
    "run_ingest_pipeline_docs": (".pipeline", "run_ingest_pipeline_docs"),
    "run_ingest_pipeline_path": (".pipeline", "run_ingest_pipeline_path"),
    "spec_hash": (".pipeline_definitions", "spec_hash"),
}

__all__ = [
    "iter_ingest_pipeline",
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
    "ingest_csv_to_chunks",
    "ingest_docs_to_chunks",
    "build_index_from_csv",
    "retrieve",
    "ask",
    "parse_filters",
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
