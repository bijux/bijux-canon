# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Application services and orchestration for bijux-canon-ingest."""

from __future__ import annotations

from .api import (
    full_rag_api,
    full_rag_api_docs,
    full_rag_api_path,
    iter_chunks_from_cleaned,
    iter_rag,
    iter_rag_core,
)
from .observability import DebugConfig, Observations, RagTaps, RagTraceV3, TraceLens
from .pipelines import (
    ErrorPolicy,
    OperatorSpec,
    PipelineConfig,
    PipelineSpec,
    SpecRegistry,
    StepConfig,
    beam_available,
    build_rag_pipeline,
    canonical_json,
    compile_to_beam,
    compile_to_dask_bag,
    dask_available,
    reconstruct_pipeline,
    spec_hash,
)
from .rag import (
    IndexBackend,
    RagApp,
    RagBuildConfig,
    RagIndex,
    ask,
    build_index_from_csv,
    ingest_csv_to_chunks,
    ingest_docs_to_chunks,
    parse_filters,
    retrieve,
)

__all__ = [
    "iter_rag",
    "iter_rag_core",
    "iter_chunks_from_cleaned",
    "full_rag_api",
    "full_rag_api_docs",
    "full_rag_api_path",
    "DebugConfig",
    "RagTaps",
    "Observations",
    "TraceLens",
    "RagTraceV3",
    "IndexBackend",
    "RagBuildConfig",
    "RagIndex",
    "RagApp",
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
