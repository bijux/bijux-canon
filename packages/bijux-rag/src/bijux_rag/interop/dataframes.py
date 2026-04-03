# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Bijux RAG Core 3: optional dataframe-style processing helpers (end-of-Bijux RAG).

These functions provide FP-style transforms for dataframes when libraries are
available (pandas/polars/dask). When they are not, callers can use the
record-based helpers (list[dict]) which require only stdlib.
"""

from __future__ import annotations

import importlib
from typing import Any


def _import(name: str) -> Any | None:
    try:
        return importlib.import_module(name)
    except Exception:
        return None


PANDAS = _import("pandas")
POLARS = _import("polars")
DASK = _import("dask.dataframe")

PANDAS_AVAILABLE = PANDAS is not None
POLARS_AVAILABLE = POLARS is not None
DASK_AVAILABLE = DASK is not None


def normalize_records(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Pure normalizer for in-memory records: strips + lowercases abstract."""

    out: list[dict[str, Any]] = []
    for row in rows:
        abstract = str(row.get("abstract", ""))
        clean = " ".join(abstract.strip().lower().split())
        out.append({**row, "clean_abstract": clean})
    return out


def pandas_clean_abstract(df: Any) -> Any:
    if not PANDAS_AVAILABLE:
        raise ImportError("pandas not available")
    return df.assign(clean_abstract=lambda d: d["abstract"].astype(str).str.strip().str.lower())


def pandas_filter_ai(df: Any) -> Any:
    if not PANDAS_AVAILABLE:
        raise ImportError("pandas not available")
    return df.loc[lambda d: d["categories"].astype(str).str.contains("cs.AI", na=False)]


__all__ = [
    "PANDAS_AVAILABLE",
    "POLARS_AVAILABLE",
    "DASK_AVAILABLE",
    "normalize_records",
    "pandas_clean_abstract",
    "pandas_filter_ai",
]
