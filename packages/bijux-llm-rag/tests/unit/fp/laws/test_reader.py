# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import hypothesis.strategies as st
from hypothesis import given, settings

from bijux_rag.fp.effects.reader import Reader, ask, local, pure

settings.register_profile("ci", max_examples=250, derandomize=True, deadline=None)
settings.load_profile("ci")


@dataclass(frozen=True)
class Cfg:
    inc: int
    mul: int


cfgs = st.builds(Cfg, inc=st.integers(-5, 5), mul=st.integers(-5, 5))


@st.composite
def st_reader(draw) -> Reader[Cfg, int]:
    base = draw(st.integers(-10, 10))
    a = draw(st.integers(-5, 5))
    b = draw(st.integers(-5, 5))
    pick = draw(st.sampled_from(["inc", "mul", "both"]))

    def run(cfg: Cfg) -> int:
        if pick == "inc":
            return base + a * cfg.inc
        if pick == "mul":
            return base + b * cfg.mul
        return base + a * cfg.inc + b * cfg.mul

    return Reader(run)


@st.composite
def st_func_to_reader(draw) -> Callable[[int], Reader[Cfg, int]]:
    a = draw(st.integers(-5, 5))
    b = draw(st.integers(-5, 5))
    c = draw(st.integers(-5, 5))

    def f(x: int) -> Reader[Cfg, int]:
        return Reader(lambda cfg: x + a * cfg.inc + b * cfg.mul + c)

    return f


@given(x=st.integers(-20, 20), f=st_func_to_reader(), cfg=cfgs)
def test_reader_left_identity(x: int, f: Callable[[int], Reader[Cfg, int]], cfg: Cfg) -> None:
    assert pure(x).and_then(f).run(cfg) == f(x).run(cfg)


@given(r=st_reader(), cfg=cfgs)
def test_reader_right_identity(r: Reader[Cfg, int], cfg: Cfg) -> None:
    assert r.and_then(pure).run(cfg) == r.run(cfg)


@given(r=st_reader(), f=st_func_to_reader(), g=st_func_to_reader(), cfg=cfgs)
def test_reader_associativity(
    r: Reader[Cfg, int],
    f: Callable[[int], Reader[Cfg, int]],
    g: Callable[[int], Reader[Cfg, int]],
    cfg: Cfg,
) -> None:
    left = r.and_then(f).and_then(g).run(cfg)
    right = r.and_then(lambda x: f(x).and_then(g)).run(cfg)
    assert left == right


@given(cfg=cfgs)
def test_reader_ask_identity(cfg: Cfg) -> None:
    assert ask().map(lambda c: c).run(cfg) == ask().run(cfg)


@given(cfg=cfgs, a=st.integers(-5, 5), b=st.integers(-5, 5))
def test_reader_local_composition(cfg: Cfg, a: int, b: int) -> None:
    r = Reader(lambda c: c.inc - c.mul)

    def f(c: Cfg) -> Cfg:
        return Cfg(inc=c.inc + a, mul=c.mul)

    def g(c: Cfg) -> Cfg:
        return Cfg(inc=c.inc, mul=c.mul + b)

    left = local(f, local(g, r)).run(cfg)
    right = local(lambda c: f(g(c)), r).run(cfg)
    assert left == right
