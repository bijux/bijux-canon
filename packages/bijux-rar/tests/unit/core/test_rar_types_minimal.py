# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from bijux_rar.core.rar_types import Claim, ClaimStatus, ClaimType, ProblemSpec, SupportKind, SupportRef


def test_problem_spec_with_content_id() -> None:
    spec = ProblemSpec(description="x", constraints={"y": 1})
    spec2 = spec.with_content_id()
    assert spec2.id
    assert spec2.id == spec2.with_content_id().id  # stable


def test_claim_supports_require_span_and_hash() -> None:
    sup = SupportRef(
        kind=SupportKind.evidence,
        ref_id="ev1",
        span=(0, 2),
        snippet_sha256="0" * 64,
    )
    c = Claim(
        statement="answer [evidence:ev1:0-2:" + "0" * 64 + "]",
        status=ClaimStatus.proposed,
        confidence=0.5,
        supports=[sup],
        claim_type=ClaimType.derived,
    )
    assert c.id  # stable id computed
