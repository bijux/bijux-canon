# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import json

from hypothesis import given
from hypothesis import strategies as st

from bijux_rag.policies.reports import fold_error_report, report_to_jsonable
from bijux_rag.result import Err, Ok, make_errinfo, map_result_iter


@given(items=st.lists(st.integers()))
def test_report_completeness(items: list[int]) -> None:
    def f(x: int):
        return Err(make_errinfo(f"C{x}", f"msg{x}", "stage", (x,))) if x % 2 else Ok(x)

    report = fold_error_report(map_result_iter(f, items))
    assert report.total_errs == sum(1 for x in items if x % 2)
    assert report.total_items == len(items)


@given(items=st.lists(st.integers(), unique=True))
def test_report_sample_ordering(items: list[int]) -> None:
    def f(x: int):
        return Err(make_errinfo("ERR", f"msg{x}", "s", (x,))) if x % 2 != 0 else Ok(x)

    report = fold_error_report(map_result_iter(f, items))
    group = report.by_code.get("ERR")
    if group is None or not group.samples:
        return

    samples = group.samples
    sample_xs = [int(s.msg[3:]) for s in samples]
    positions = [next(i for i, x in enumerate(items) if x == sx and x % 2 != 0) for sx in sample_xs]
    assert positions == sorted(positions)


@given(items=st.lists(st.integers()))
def test_report_bounded_memory(items: list[int]) -> None:
    report = fold_error_report(map_result_iter(lambda _x: Err("E"), items), max_samples=10)
    assert all(len(g.samples) <= 10 for g in report.by_code.values())


def test_report_to_jsonable_is_json_serializable() -> None:
    items = [1, 2, 3, 4, 5]

    def f(x: int):
        return Err(make_errinfo("ERR", f"msg{x}", "stage", (x,))) if x % 2 else Ok(x)

    report = fold_error_report(map_result_iter(f, items), max_samples=2, path_depth=2)
    payload = report_to_jsonable(report)
    assert "by_path_prefix" in payload
    json.dumps(payload)
