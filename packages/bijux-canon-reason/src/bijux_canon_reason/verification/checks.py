# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from bijux_canon_reason.core.types import VerificationCheck, VerificationFailure
from bijux_canon_reason.verification.check_registry import CHECK_SEQUENCE
from bijux_canon_reason.verification.context import VerificationContext
def run_all_checks(
    ctx: VerificationContext,
) -> tuple[list[VerificationCheck], list[VerificationFailure]]:
    checks: list[VerificationCheck] = []
    failures: list[VerificationFailure] = []
    for fn in CHECK_SEQUENCE:
        c, f = fn(ctx)
        checks.append(c)
        failures.extend(f)
    return checks, failures
