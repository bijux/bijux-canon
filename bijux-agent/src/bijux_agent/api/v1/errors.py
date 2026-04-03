"""API v1 error taxonomy and HTTP mapping."""

from __future__ import annotations

from enum import Enum


class APIErrorCode(str, Enum):
    """Stable error codes exposed by the API layer."""

    INVALID_REQUEST = "INVALID_REQUEST"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    EXECUTION_FAILED = "EXECUTION_FAILED"
    CONVERGENCE_FAILED = "CONVERGENCE_FAILED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


HTTP_STATUS_BY_CODE: dict[APIErrorCode, int] = {
    APIErrorCode.INVALID_REQUEST: 400,
    APIErrorCode.VALIDATION_ERROR: 400,
    APIErrorCode.EXECUTION_FAILED: 422,
    APIErrorCode.CONVERGENCE_FAILED: 422,
    APIErrorCode.INTERNAL_ERROR: 500,
}
