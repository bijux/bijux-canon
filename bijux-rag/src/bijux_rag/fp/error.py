# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Bijux RAG error codes and thin ErrInfo re-exports (end-of-Bijux RAG)."""

from __future__ import annotations

from enum import Enum

from bijux_rag.result.types import ErrInfo, make_errinfo


class ErrorCode(str, Enum):
    RATE_LIMIT = "RATE_LIMIT"
    TIMEOUT = "TIMEOUT"
    TRANSIENT = "TRANSIENT"
    RETRYABLE = "RETRYABLE"
    EMBED_FAIL = "EMBED_FAIL"
    INTERNAL = "INTERNAL"
    EMB_MODEL_MISMATCH = "EMB_MODEL_MISMATCH"
    EMB_DIM_MISMATCH = "EMB_DIM_MISMATCH"


__all__ = ["ErrorCode", "ErrInfo", "make_errinfo"]
