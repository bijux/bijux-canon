# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""FAISS persistence adapters."""

from __future__ import annotations

from .exact import (
    DenseVectorRecord,
    FaissExactIndex,
    FaissExactIndexCorruptionError,
    FaissExactIndexManifest,
    FaissExactSearchResult,
)
from .hnsw import (
    FaissHnswIndex,
    FaissHnswIndexCorruptionError,
    FaissHnswIndexManifest,
    FaissHnswSearchResult,
    HnswParameters,
    HnswRecallMeasurement,
    measure_hnsw_recall,
)

__all__ = [
    "DenseVectorRecord",
    "FaissExactIndex",
    "FaissExactIndexCorruptionError",
    "FaissExactIndexManifest",
    "FaissExactSearchResult",
    "FaissHnswIndex",
    "FaissHnswIndexCorruptionError",
    "FaissHnswIndexManifest",
    "FaissHnswSearchResult",
    "HnswParameters",
    "HnswRecallMeasurement",
    "measure_hnsw_recall",
]
