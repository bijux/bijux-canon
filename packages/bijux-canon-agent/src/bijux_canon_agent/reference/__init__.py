"""Reference pipelines intended for documentation and adoption."""

from __future__ import annotations

from .document_review import DocumentReviewPipeline, run_document_review
from .minimal import MinimalPipeline, run_minimal

__all__ = [
    "MinimalPipeline",
    "run_minimal",
    "DocumentReviewPipeline",
    "run_document_review",
]
