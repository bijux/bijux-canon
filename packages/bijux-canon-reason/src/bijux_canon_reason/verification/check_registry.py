# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from collections.abc import Callable

from bijux_canon_reason.core.types import VerificationCheck, VerificationFailure
from bijux_canon_reason.verification.context import VerificationContext
from bijux_canon_reason.verification.provenance_checks import (
    check_derived_grounding,
    check_evidence_hashes,
    check_reasoning_trace,
    check_support_spans,
)
from bijux_canon_reason.verification.structural_checks import (
    check_claim_supports,
    check_core_invariants,
    check_finalize_validated,
    check_insufficient_reasoning,
    check_required_steps,
    check_tool_linkage,
)

VerificationCheckFn = Callable[
    [VerificationContext],
    tuple[VerificationCheck, list[VerificationFailure]],
]

CHECK_SEQUENCE: tuple[VerificationCheckFn, ...] = (
    check_core_invariants,
    check_tool_linkage,
    check_claim_supports,
    check_derived_grounding,
    check_reasoning_trace,
    check_insufficient_reasoning,
    check_finalize_validated,
    check_required_steps,
    check_evidence_hashes,
    check_support_spans,
)

__all__ = ["CHECK_SEQUENCE", "VerificationCheckFn"]
