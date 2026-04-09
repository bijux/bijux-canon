# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from typing import Any, cast

from bijux_canon_reason.evaluation.suite_workflow import suite_summary


def test_suite_summary_handles_empty_and_taxonomy() -> None:
    empty = cast(dict[str, Any], suite_summary([]))
    assert empty["count"] == 0
    assert empty["failure_taxonomy"] == {}

    results = [
        {
            "recall_at_k": 1.0,
            "mrr": 1.0,
            "alignment_rate": 1.0,
            "faithfulness": 1.0,
            "insufficient": False,
            "failure_taxonomy": {"core": 1},
        },
        {
            "recall_at_k": 0.0,
            "mrr": 0.0,
            "alignment_rate": 0.0,
            "faithfulness": 0.0,
            "insufficient": True,
            "failure_taxonomy": {"core": 2},
        },
    ]
    summary = cast(dict[str, Any], suite_summary(results))
    assert summary["count"] == 2
    assert summary["insufficient_rate"] == 0.5
    failure_taxonomy = cast(dict[str, int], summary["failure_taxonomy"])
    assert failure_taxonomy["core"] == 3
