# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from itertools import islice

import pytest

from bijux_rag import (
    Chunk,
    ChunkWithoutEmbedding,
    FakeTime,
    RagConfig,
    RagEnv,
    RawDoc,
    TraceLens,
    _trace_iter,
    compose_transforms,
    fence_k,
    fork2_lockstep,
    gen_bounded_chunks,
    gen_overlapping_chunks,
    get_deps,
    make_gen_rag_fn,
    make_peek,
    make_sampler_stable,
    multicast,
    sliding_windows,
    structural_dedup_lazy,
    throttle,
)


def test_dedup_iterator_preserves_order() -> None:
    a = Chunk(doc_id="d1", text="x", start=0, end=1, metadata={}, embedding=(0.1,) * 16)
    a2 = Chunk(
        doc_id="d1", text="x", start=0, end=1, metadata={}, embedding=(0.9,) * 16
    )  # considered duplicate by structural key
    b = Chunk(doc_id="d1", text="y", start=1, end=2, metadata={}, embedding=(0.2,) * 16)
    c = Chunk(doc_id="d2", text="x", start=0, end=1, metadata={}, embedding=(0.3,) * 16)

    out = list(structural_dedup_lazy([a, b, a2, c, a]))
    assert out == [a, b, c]


def _reconstruct_overlap(chunks: list[ChunkWithoutEmbedding], o: int, *, strip_nuls: bool) -> str:
    if not chunks:
        return ""
    out = chunks[0].text
    for c in chunks[1:]:
        out += c.text[o:]
    if strip_nuls:
        out = out.rstrip("\0")
    return out


def test_overlapping_coverage_emit_short() -> None:
    text = "abcdefghij"
    chunks = list(gen_overlapping_chunks("id", text, k=4, o=2, tail_policy="emit_short"))
    assert _reconstruct_overlap(chunks, 2, strip_nuls=False) == text


def test_overlapping_coverage_pad() -> None:
    text = "abcdefghij"
    chunks = list(gen_overlapping_chunks("id", text, k=4, o=2, tail_policy="pad"))
    assert _reconstruct_overlap(chunks, 2, strip_nuls=True) == text


def test_overlapping_drop_covers_prefix() -> None:
    text = "abcdefghij"
    chunks = list(gen_overlapping_chunks("id", text, k=4, o=2, tail_policy="drop"))
    rec = _reconstruct_overlap(chunks, 2, strip_nuls=False)
    assert text.startswith(rec)
    assert len(text) - len(rec) < (4 - 2)


def test_sliding_windows_demand_bound() -> None:
    pulls = 0

    def counted() -> int:
        nonlocal pulls
        pulls += 1
        return pulls - 1

    def src(n: int):
        for _ in range(n):
            yield counted()

    w = 4
    n_windows = 3
    windows = sliding_windows(src(100), w)
    got = list(islice(windows, n_windows))
    assert len(got) == n_windows
    assert pulls == n_windows + (w - 1)


def test_multicast_independence() -> None:
    a, b = multicast(range(10), 2, maxlen=3)
    out_a: list[int] = []
    out_b: list[int] = []
    for _ in range(10):
        out_a.append(next(a))
        out_b.append(next(b))
    assert out_a == list(range(10))
    assert out_b == list(range(10))


def test_multicast_buffer_error_on_excess_skew() -> None:
    a, b = multicast(range(10), 2, maxlen=1)
    assert next(a) == 0
    assert next(b) == 0
    assert next(a) == 1
    with pytest.raises(BufferError):
        next(a)  # would force buffering past maxlen for b


def test_throttle_uses_injected_clock() -> None:
    ft = FakeTime()
    out = list(throttle([1, 2, 3], min_delta=0.5, clock=ft.clock, sleeper=ft.sleep))
    assert out == [1, 2, 3]
    assert ft.sleeps == [0.5, 0.5]
    assert ft.clock() == 1.0


def test_trace_neutrality_and_bounded_samples() -> None:
    lens: TraceLens[int] = TraceLens(limit=2)
    xs = [1, 2, 3, 4, 5]
    out = list(_trace_iter(xs, lens))
    assert out == xs
    assert lens.count == 5
    assert lens.samples == [1, 2]


def test_make_gen_rag_fn_equivalence() -> None:
    docs = [
        RawDoc("d1", "t", "a" * 200, "cs.AI"),
        RawDoc("d2", "t", "b" * 200, "cs.AI"),
    ]
    rag_fn = make_gen_rag_fn(chunk_size=50, max_chunks=3)
    out1 = list(rag_fn(docs))

    config = RagConfig(env=RagEnv(50))
    deps = get_deps(config)
    out2 = list(gen_bounded_chunks(docs, config, deps, max_chunks=3))
    assert out1 == out2


def test_fork2_lockstep_pairs_values() -> None:
    def inc(xs):
        return (x + 1 for x in xs)

    def dec(xs):
        return (x - 1 for x in xs)

    stage = fork2_lockstep(inc, dec)
    assert list(stage([1, 2, 3])) == [(2, 0), (3, 1), (4, 2)]


def test_fork2_lockstep_mismatch_raises() -> None:
    def inc(xs):
        return (x + 1 for x in xs)

    def identity_iter(xs):
        return iter(xs)

    shorter = compose_transforms(fence_k(2), identity_iter)
    stage = fork2_lockstep(inc, shorter)
    with pytest.raises(ValueError):
        list(stage([1, 2, 3]))


def test_sampler_stable_order_insensitive() -> None:
    xs = ["a", "b", "c", "d", "e", "f"]
    samp = make_sampler_stable(0.5, key=lambda s: s.encode("utf-8"))
    out1 = list(samp(xs))
    out2 = list(samp(list(reversed(xs))))
    assert sorted(out1) == sorted(out2)


def test_peek_is_value_neutral_and_bounded() -> None:
    peeks: list[tuple[int, ...]] = []
    stage = make_peek(3, lambda t: peeks.append(t), stride=2)
    xs = list(range(10))
    assert list(stage(xs)) == xs
    assert all(len(p) == 3 for p in peeks)
