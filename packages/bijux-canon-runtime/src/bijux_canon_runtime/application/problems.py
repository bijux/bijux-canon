# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Transport-neutral safe Runtime problem details."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import re
from typing import TypeAlias


RuntimeProblemFields: TypeAlias = dict[str, object]


class RuntimeProblemCode(StrEnum):
    """Stable machine-readable application failure codes."""

    INVALID_REQUEST = "invalid-request"
    NOT_FOUND = "not-found"
    UNSUPPORTED_VERSION = "unsupported-version"
    CONFLICT = "conflict"
    OPERATION_FAILED = "operation-failed"
    MISSING_CAPABILITY = "missing-capability"


@dataclass(frozen=True, slots=True)
class RuntimeProblem:
    """Safe problem fields shared by library, CLI, and HTTP."""

    schema_version: str
    type: str
    title: str
    status: int
    code: RuntimeProblemCode
    correlation_id: str
    run_id: str | None
    retryable: bool
    remediation: str
    cause: str | None


_DEFINITIONS: dict[RuntimeProblemCode, tuple[int, str, bool, str]] = {
    RuntimeProblemCode.INVALID_REQUEST: (
        400,
        "Application request is invalid",
        False,
        "Correct the request without changing its idempotency key.",
    ),
    RuntimeProblemCode.NOT_FOUND: (
        404,
        "Runtime resource not found",
        False,
        "Use an identity returned by this configured Runtime store.",
    ),
    RuntimeProblemCode.UNSUPPORTED_VERSION: (
        406,
        "Unsupported API version",
        False,
        "Send Bijux-API-Version: v2.",
    ),
    RuntimeProblemCode.CONFLICT: (
        409,
        "Durable job state conflicts with the request",
        False,
        "Inspect the existing job before retrying.",
    ),
    RuntimeProblemCode.OPERATION_FAILED: (
        500,
        "Runtime application operation failed",
        True,
        "Inspect persisted evidence and retry.",
    ),
    RuntimeProblemCode.MISSING_CAPABILITY: (
        503,
        "Runtime application service is unavailable",
        True,
        "Configure the v2 application service composition.",
    ),
}
_SECRET = re.compile(
    r"(?i)(api[-_ ]?key|authorization|password|secret|token)\s*[:=]\s*\S+"
)
_ABSOLUTE_PATH = re.compile(r"(?<![A-Za-z0-9_.-])/(?:[^\s:/]+/)+[^\s:]*")


def runtime_problem(
    code: RuntimeProblemCode,
    *,
    correlation_id: str | None = None,
    run_id: str | None = None,
    cause: object | None = None,
) -> RuntimeProblem:
    """Create one versioned problem with sanitized bounded diagnostics."""
    status, title, retryable, remediation = _DEFINITIONS[code]
    return RuntimeProblem(
        schema_version="bijux.runtime.problem.v2",
        type=f"https://bijux.org/problems/runtime/{code.value}",
        title=title,
        status=status,
        code=code,
        correlation_id=_safe_identity(correlation_id, "correlation-unavailable"),
        run_id=None if run_id is None else _safe_identity(run_id, "run-unavailable"),
        retryable=retryable,
        remediation=remediation,
        cause=_safe_cause(cause),
    )


def runtime_problem_fields(problem: RuntimeProblem) -> RuntimeProblemFields:
    """Return canonical fields for transports, structured logs, and traces."""
    return {
        "cause": problem.cause,
        "code": problem.code.value,
        "correlation_id": problem.correlation_id,
        "remediation": problem.remediation,
        "retryable": problem.retryable,
        "run_id": problem.run_id,
        "schema_version": problem.schema_version,
        "status": problem.status,
        "title": problem.title,
        "type": problem.type,
    }


def _safe_identity(value: str | None, fallback: str) -> str:
    if value is None or re.fullmatch(r"[A-Za-z0-9._:-]{1,200}", value) is None:
        return fallback
    return value


def _safe_cause(cause: object | None) -> str | None:
    if cause is None:
        return None
    value = " ".join(str(cause).split())
    value = _SECRET.sub(r"\1=<redacted>", value)
    value = _ABSOLUTE_PATH.sub("<path>", value)
    return value[:500] or type(cause).__name__


__all__ = [
    "RuntimeProblem",
    "RuntimeProblemCode",
    "RuntimeProblemFields",
    "runtime_problem",
    "runtime_problem_fields",
]
