# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from collections import defaultdict

from hypothesis import given
from hypothesis import strategies as st

from bijux_rag.policies.retries import RetryDecision, fixed_policy, retry_map_iter
from bijux_rag.result import Err, Ok


@given(items=st.lists(st.integers()))
def test_bounded_attempts(items: list[int]) -> None:
    tagged = list(enumerate(items))
    attempts: dict[int, int] = defaultdict(int)

    def fn(iv: tuple[int, int]):
        i, v = iv
        attempts[i] += 1
        return Ok(v) if attempts[i] >= 3 else Err("TRANSIENT")

    list(
        retry_map_iter(
            fn,
            tagged,
            classifier=lambda e: e == "TRANSIENT",
            policy=fixed_policy(5),
            stage="test",
            max_attempts=10,
        )
    )
    assert all(a <= 5 for a in attempts.values())


def test_engine_cap_overrides_policy() -> None:
    attempts = [0]

    def fn(_):
        attempts[0] += 1
        return Err("TRANSIENT")

    def always_retry(_):
        return RetryDecision(True, None)

    list(
        retry_map_iter(
            fn,
            [0],
            classifier=lambda _: True,
            policy=always_retry,
            stage="test",
            max_attempts=4,
        )
    )
    assert attempts[0] == 4


@given(items=st.lists(st.integers(), min_size=10))
def test_fairness_interleaving(items: list[int]) -> None:
    tagged = list(enumerate(items))
    attempts: dict[int, int] = defaultdict(int)

    def fn(iv: tuple[int, int]):
        i, v = iv
        attempts[i] += 1
        return Ok(v) if attempts[i] >= 2 else Err("TRANSIENT")

    list(
        retry_map_iter(
            fn,
            tagged,
            classifier=lambda _: True,
            policy=fixed_policy(3),
            stage="test",
            inflight_cap=4,
        )
    )

    assert max(attempts.values()) <= min(attempts.values()) + 1


@given(items=st.lists(st.integers()))
def test_retry_completion(items: list[int]) -> None:
    tagged = list(enumerate(items))
    attempts: dict[int, int] = defaultdict(int)

    def fn(iv: tuple[int, int]):
        i, v = iv
        attempts[i] += 1
        needed = (v % 5) + 1
        return Ok(iv) if attempts[i] >= needed else Err("TRANSIENT")

    results = list(
        retry_map_iter(
            fn,
            tagged,
            classifier=lambda _: True,
            policy=fixed_policy(10),
            stage="test",
            inflight_cap=32,
        )
    )
    assert len(results) == len(items)


@given(items=st.lists(st.integers()))
def test_final_err_annotation_skips_plain_str(items: list[int]) -> None:
    def fn(_x: int):
        return Err("TRANSIENT")

    out = list(
        retry_map_iter(
            fn,
            items,
            classifier=lambda _: True,
            policy=fixed_policy(3),
            stage="test",
            max_attempts=5,
        )
    )
    for r in out:
        assert isinstance(r, Err)
        assert r.error == "TRANSIENT"
