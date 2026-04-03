# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from bijux_canon_ingest.observability import DebugConfig, IngestTaps, IngestTrace, Observations


def test_ingest_taps_keeps_extra_hooks_per_instance() -> None:
    first = IngestTaps()
    second = IngestTaps(extra={"chunks": lambda items: None})

    assert first.extra == {}
    assert "chunks" in second.extra


def test_observations_preserve_deterministic_summary_fields() -> None:
    observations = Observations(
        total_docs=2,
        total_chunks=3,
        kept_docs=2,
        cleaned_docs=2,
        sample_doc_ids=("d1", "d2"),
        sample_chunk_starts=(0, 64),
        warnings=("truncated",),
    )

    assert observations.total_docs == 2
    assert observations.sample_doc_ids == ("d1", "d2")
    assert observations.sample_chunk_starts == (0, 64)
    assert observations.warnings == ("truncated",)


def test_ingest_trace_uses_independent_trace_lenses() -> None:
    trace = IngestTrace()
    trace.docs.note("doc")
    trace.cleaned.note("clean")
    trace.chunks.note("chunk")
    trace.embedded.note("embedded")

    assert trace.docs.samples == ["doc"]
    assert trace.cleaned.samples == ["clean"]
    assert trace.chunks.samples == ["chunk"]
    assert trace.embedded.samples == ["embedded"]


def test_debug_config_defaults_to_disabled_tracing() -> None:
    config = DebugConfig()

    assert not config.trace_docs
    assert not config.trace_kept
    assert not config.trace_clean
    assert not config.trace_chunks
    assert not config.trace_embedded
    assert not config.probe_chunks
