# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from pathlib import Path

from bijux_rar.core.fingerprints import fingerprint_obj
from bijux_rar.core.rar_types import (
    Plan,
    Trace,
    VerificationFailure,
    VerificationPolicyMode,
    VerificationReport,
    VerificationSeverity,
)
from bijux_rar.rar.verification.checks import VerificationContext, run_all_checks


def verify_trace(
    *,
    trace: Trace,
    plan: Plan,
    artifacts_dir: Path | None = None,
    policy: VerificationPolicyMode = VerificationPolicyMode.strict,
) -> VerificationReport:
    ctx = VerificationContext(trace=trace, plan=plan, artifacts_dir=artifacts_dir)
    checks, failures = run_all_checks(ctx)
    filtered_failures: list[VerificationFailure] = list(failures)
    if policy == VerificationPolicyMode.permissive:
        filtered_failures = [
            f for f in failures if f.severity == VerificationSeverity.error
        ]
    elif policy == VerificationPolicyMode.audit:
        # keep all failures, but mark severity for summary
        filtered_failures = list(failures)

    rid = fingerprint_obj(
        {
            "checks": [c.model_dump(mode="json") for c in checks],
            "failures": [f.model_dump(mode="json") for f in filtered_failures],
        }
    )
    failed = sum(1 for c in checks if not c.passed)
    total = len(checks)
    return VerificationReport(
        id=rid,
        checks=checks,
        failures=filtered_failures,
        summary_metrics={
            "failures": float(len(filtered_failures)),
            "checks_failed": failed,
            "checks_total": total,
        },
    )
