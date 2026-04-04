# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Public core exports for authority, failures, and stable identifiers."""

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
from bijux_canon_runtime.core.ids import ActionID
from bijux_canon_runtime.core.ids import AgentID
from bijux_canon_runtime.core.ids import ArtifactID
from bijux_canon_runtime.core.ids import BundleID
from bijux_canon_runtime.core.ids import ClaimID
from bijux_canon_runtime.core.ids import ContentHash
from bijux_canon_runtime.core.ids import ContractID
from bijux_canon_runtime.core.ids import DatasetID
from bijux_canon_runtime.core.ids import EnvironmentFingerprint
from bijux_canon_runtime.core.ids import EvidenceID
from bijux_canon_runtime.core.ids import FlowID
from bijux_canon_runtime.core.ids import GateID
from bijux_canon_runtime.core.ids import InputsFingerprint
from bijux_canon_runtime.core.ids import PlanHash
from bijux_canon_runtime.core.ids import PolicyFingerprint
from bijux_canon_runtime.core.ids import RequestID
from bijux_canon_runtime.core.ids import ResolverID
from bijux_canon_runtime.core.ids import RuleID
from bijux_canon_runtime.core.ids import RunID
from bijux_canon_runtime.core.ids import StepID
from bijux_canon_runtime.core.ids import TenantID
from bijux_canon_runtime.core.ids import ToolID
from bijux_canon_runtime.core.ids import VersionID

__all__ = [
    "ActionID",
    "AgentID",
    "ArtifactID",
    "AuthorityToken",
    "BundleID",
    "ClaimID",
    "ContentHash",
    "ContractID",
    "DatasetID",
    "EnvironmentFingerprint",
    "EvidenceID",
    "ExecutionFailure",
    "FlowID",
    "GateID",
    "InputsFingerprint",
    "PlanHash",
    "PolicyFingerprint",
    "ReasoningFailure",
    "RequestID",
    "ResolverID",
    "ResolutionFailure",
    "RuleID",
    "RunID",
    "RetrievalFailure",
    "SEMANTICS_SOURCE",
    "SEMANTICS_VERSION",
    "SemanticViolationError",
    "StepID",
    "TenantID",
    "ToolID",
    "VerificationFailure",
    "VersionID",
    "authority_token",
    "enforce_runtime_semantics",
    "finalize_trace",
]
