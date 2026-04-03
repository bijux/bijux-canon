# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Module definitions for core/__init__.py."""

from __future__ import annotations

from bijux_canon_runtime.core.authority import (
    SEMANTICS_SOURCE,
    SEMANTICS_VERSION,
    AuthorityToken,
    authority_token,
    enforce_runtime_semantics,
    finalize_trace,
)
from bijux_canon_runtime.core.errors import (
    ExecutionFailure,
    ReasoningFailure,
    ResolutionFailure,
    RetrievalFailure,
    SemanticViolationError,
    VerificationFailure,
)
from bijux_canon_runtime.core.ids import *  # noqa: F403

__all__ = [
    "AuthorityToken",
    "ExecutionFailure",
    "ReasoningFailure",
    "ResolutionFailure",
    "RetrievalFailure",
    "SEMANTICS_SOURCE",
    "SEMANTICS_VERSION",
    "SemanticViolationError",
    "VerificationFailure",
    "authority_token",
    "enforce_runtime_semantics",
    "finalize_trace",
]
__all__ += [  # type: ignore[list-item]
    name for name in globals() if name.endswith("ID") or name.endswith("Fingerprint")
]
