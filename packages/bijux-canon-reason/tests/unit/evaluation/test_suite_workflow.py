# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, cast

from bijux_canon_reason.core.types import Claim, EvidenceRef, SupportKind, SupportRef
from bijux_canon_reason.evaluation.suite_workflow import (
    _exact_evidence_support_count,
    suite_summary,
)


def test_exact_support_diagnostic_recomputes_retained_bytes(tmp_path: Path) -> None:
    exact = b"Exact retained evidence."
    evidence_path = tmp_path / "evidence" / "source.txt"
    evidence_path.parent.mkdir()
    evidence_path.write_bytes(exact)
    evidence = EvidenceRef(
        uri="file:///source.txt",
        sha256=hashlib.sha256(exact).hexdigest(),
        span=(0, len(exact)),
        chunk_id=hashlib.sha256(exact).hexdigest(),
        content_path="evidence/source.txt",
    ).with_content_id()
    support = SupportRef(
        kind=SupportKind.evidence,
        ref_id=evidence.id,
        span=(0, len(exact)),
        snippet_sha256=hashlib.sha256(exact).hexdigest(),
    )
    claim = Claim(statement=exact.decode(), supports=[support]).with_content_id()

    assert (
        _exact_evidence_support_count(
            run_dir=tmp_path,
            evidence_by_id={evidence.id: evidence},
            claim=claim,
        )
        == 1
    )

    evidence_path.write_bytes(b"Changed retained evidence.")
    assert (
        _exact_evidence_support_count(
            run_dir=tmp_path,
            evidence_by_id={evidence.id: evidence},
            claim=claim,
        )
        is None
    )


def test_suite_summary_aggregates_metrics(tmp_path: Path) -> None:
    results = [
        {
            "exact_support_rate": 1.0,
            "support_links_per_supported_claim": 1.0,
            "insufficient": False,
            "failure_taxonomy": {},
        },
        {
            "exact_support_rate": 0.5,
            "support_links_per_supported_claim": 0.5,
            "insufficient": True,
            "failure_taxonomy": {"core_invariants": 1},
        },
    ]
    summary = cast(dict[str, Any], suite_summary(results))
    assert summary["count"] == 2
    assert summary["insufficient_rate"] == 0.5
    failure_taxonomy = cast(dict[str, int], summary["failure_taxonomy"])
    assert failure_taxonomy["core_invariants"] == 1
