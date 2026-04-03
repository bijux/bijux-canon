# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Application services and orchestration for bijux-canon-ingest."""

from __future__ import annotations

from .pipeline import (
    run_ingest_pipeline,
    run_ingest_pipeline_docs,
    run_ingest_pipeline_path,
    iter_chunks_from_cleaned,
    iter_ingest_pipeline,
    iter_ingest_pipeline_core,
)
from .indexing import (
    IndexBuildConfig,
    build_index_from_csv,
    ingest_csv_to_chunks,
    ingest_docs_to_chunks,
)
from .querying import ask, parse_filters, retrieve
from bijux_canon_ingest.observability import (
    DebugConfig,
    Observations,
    RagTaps,
    RagTraceV3,
    TraceLens,
)
from .pipeline_definitions import (
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
from .service import (
    IndexBackend,
    IngestService,
    StoredIndex,
)

__all__ = [
    "iter_ingest_pipeline",
    "iter_ingest_pipeline_core",
    "iter_chunks_from_cleaned",
    "run_ingest_pipeline",
    "run_ingest_pipeline_docs",
    "run_ingest_pipeline_path",
    "DebugConfig",
    "RagTaps",
    "Observations",
    "TraceLens",
    "RagTraceV3",
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
