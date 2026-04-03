# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from pathlib import Path

from bijux_canon_reason.rar.eval.suite import suite_summary


def test_suite_summary_aggregates_metrics(tmp_path: Path) -> None:
    results = [
        {
            "recall_at_k": 1.0,
            "mrr": 1.0,
            "faithfulness": 1.0,
            "alignment_rate": 1.0,
            "insufficient": False,
            "failure_taxonomy": {},
        },
        {
            "recall_at_k": 0.0,
            "mrr": 0.5,
            "faithfulness": 0.5,
            "alignment_rate": 0.5,
            "insufficient": True,
            "failure_taxonomy": {"core_invariants": 1},
        },
    ]
    summary = suite_summary(results)
    assert summary["count"] == 2
    assert summary["insufficient_rate"] == 0.5
    assert summary["failure_taxonomy"]["core_invariants"] == 1
