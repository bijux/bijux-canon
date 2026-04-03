# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from typing import Literal

from pydantic import ConfigDict, model_validator

from bijux_canon_reason.core.models.base import JsonValue, StableModel
from bijux_canon_reason.core.models.claims import (
    Claim,
    ClaimStatus,
    ClaimType,
    EvidenceRef,
    SupportKind,
    SupportRef,
)
from bijux_canon_reason.core.models.planning import (
    Plan,
    PlanNode,
    ProblemSpec,
    StepKind,
    StepSpec,
    ToolRequest,
)
from bijux_canon_reason.core.models.trace import (
    ClaimEmittedEvent,
    DeriveOutput,
    EvidenceRegisteredEvent,
    FinalizeOutput,
    GatherOutput,
    InsufficientEvidenceOutput,
    RuntimeDescriptor,
    StepFinishedEvent,
    StepOutput,
    StepStartedEvent,
    ToolCall,
    ToolCalledEvent,
    ToolDescriptor,
    ToolResult,
    ToolReturnedEvent,
    Trace,
    TraceEvent,
    TraceEventKind,
    UnderstandOutput,
    VerifyOutput,
)
from bijux_canon_reason.core.models.verification import (
    ReplayResult,
    VerificationCheck,
    VerificationFailure,
    VerificationPolicyMode,
    VerificationReport,
    VerificationSeverity,
)
