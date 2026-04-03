# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import hypothesis.strategies as st
from hypothesis import given, settings

from bijux_rag.fp.effects.configurable import toggle_logging, toggle_metrics, toggle_validation
from bijux_rag.fp.effects.writer import Writer
from bijux_rag.result.types import Err, Ok, Result

settings.register_profile("ci", max_examples=200, derandomize=True, deadline=None)
settings.load_profile("ci")


def validate_non_negative(x: int) -> Result[int, str]:
    return Ok(x) if x >= 0 else Err("neg")


def base_step(x: int) -> Result[int, str]:
    return Ok(x * 2)


@given(x=st.integers(-20, 20), enabled=st.booleans())
def test_toggle_validation_identity_when_disabled(x: int, enabled: bool) -> None:
    toggled = toggle_validation(enabled, validate_non_negative, base_step)
    if not enabled:
        assert toggled(x) == base_step(x)


@given(x=st.integers(-20, 20))
def test_toggle_validation_matches_validate_then_pipeline(x: int) -> None:
    toggled = toggle_validation(True, validate_non_negative, base_step)
    assert toggled(x) == validate_non_negative(x).and_then(base_step)


@given(x=st.integers(-20, 20), enabled=st.booleans())
def test_toggle_metrics_projection_equivalence(x: int, enabled: bool) -> None:
    def pure_step(v: int) -> int:
        return v * 3

    def measure(inp: int, out: int) -> int:
        return inp + out

    toggled = toggle_metrics(enabled, measure, zero=0, pipeline=pure_step)
    value, metric = toggled(x)
    assert value == pure_step(x)
    assert metric == (measure(x, value) if enabled else 0)


@given(x=st.integers(-20, 20), enabled=st.booleans())
def test_toggle_logging_projection_equivalence(x: int, enabled: bool) -> None:
    def pure_step(v: int) -> int:
        return v + 1

    def mk_msg(inp: int, out: int) -> str:
        return f"{inp}->{out}"

    toggled = toggle_logging(enabled, pure_step, mk_msg)
    writer = toggled(x)
    assert isinstance(writer, Writer)
    value, logs = writer.run()
    assert value == pure_step(x)
    assert logs == ((mk_msg(x, value),) if enabled else ())
