# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from bijux_rag.pipelines.specs import OperatorSpec, PipelineSpec, reconstruct_pipeline, spec_hash
from bijux_rag.result.types import ErrInfo, Ok, Result, is_ok


def _inc(x: int) -> int:
    return x + 1


def _dup(x: int) -> list[int]:
    return [x, x]


REGISTRY = {"inc": _inc, "dup": _dup}


@given(xs=st.lists(st.integers(), max_size=200))
@settings(max_examples=100)
def test_reconstruct_pipeline_equivalence(xs: list[int]) -> None:
    spec = PipelineSpec(
        ops=(
            OperatorSpec(type="Map", func_id="inc", error_policy="collect"),
            OperatorSpec(type="FlatMap", func_id="dup", error_policy="collect"),
        )
    )

    r = reconstruct_pipeline(spec, REGISTRY)
    assert is_ok(r)
    run = r.value

    stream: list[Result[int, ErrInfo]] = [Ok(x) for x in xs]
    got = [item.value for item in run(stream) if isinstance(item, Ok)]

    expected: list[int] = []
    for x in xs:
        expected.extend([x + 1, x + 1])

    assert got == expected
    assert len(spec_hash(spec)) == 64
