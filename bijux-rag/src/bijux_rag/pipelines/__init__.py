# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Bijux RAG: pipeline building and cross-process specs (end-of-Bijux RAG)."""

from .configured import PipelineConfig, StepConfig, build_rag_pipeline
from .distributed import beam_available, compile_to_beam, compile_to_dask_bag, dask_available
from .specs import (
    ErrorPolicy,
    OperatorSpec,
    PipelineSpec,
    SpecRegistry,
    canonical_json,
    reconstruct_pipeline,
    spec_hash,
)

__all__ = [
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
