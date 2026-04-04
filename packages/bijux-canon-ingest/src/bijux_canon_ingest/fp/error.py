# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Error codes and thin ErrInfo re-exports for ingest pipelines."""

from __future__ import annotations

from enum import StrEnum

from bijux_canon_ingest.result.types import ErrInfo, make_errinfo


class ErrorCode(StrEnum):
    RATE_LIMIT = "RATE_LIMIT"
    TIMEOUT = "TIMEOUT"
    TRANSIENT = "TRANSIENT"
    RETRYABLE = "RETRYABLE"
    EMBED_FAIL = "EMBED_FAIL"
    INTERNAL = "INTERNAL"
    EMB_MODEL_MISMATCH = "EMB_MODEL_MISMATCH"
    EMB_DIM_MISMATCH = "EMB_DIM_MISMATCH"


__all__ = ["ErrorCode", "ErrInfo", "make_errinfo"]
