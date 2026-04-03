# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from bijux_rar.rar.eval.suite import suite_summary


def test_suite_summary_handles_empty_and_taxonomy() -> None:
    empty = suite_summary([])
    assert empty["count"] == 0
    assert empty["failure_taxonomy"] == {}

    results = [
        {"recall_at_k": 1.0, "mrr": 1.0, "alignment_rate": 1.0, "faithfulness": 1.0, "insufficient": False, "failure_taxonomy": {"core": 1}},
        {"recall_at_k": 0.0, "mrr": 0.0, "alignment_rate": 0.0, "faithfulness": 0.0, "insufficient": True, "failure_taxonomy": {"core": 2}},
    ]
    summary = suite_summary(results)
    assert summary["count"] == 2
    assert summary["insufficient_rate"] == 0.5
    assert summary["failure_taxonomy"]["core"] == 3
