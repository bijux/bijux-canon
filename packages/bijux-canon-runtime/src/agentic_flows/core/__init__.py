# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for core/__init__.py."""

from __future__ import annotations

from agentic_flows.core.authority import (
    SEMANTICS_SOURCE,
    SEMANTICS_VERSION,
    AuthorityToken,
    authority_token,
    enforce_runtime_semantics,
    finalize_trace,
)
from agentic_flows.core.errors import (
    ExecutionFailure,
    ReasoningFailure,
    ResolutionFailure,
    RetrievalFailure,
    SemanticViolationError,
    VerificationFailure,
)
from agentic_flows.core.ids import *  # noqa: F403

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
