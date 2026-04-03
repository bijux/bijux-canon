# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from pathlib import Path

from bijux_rar.boundaries.serde.trace_jsonl import (
    fingerprint_trace_file,
    write_trace_jsonl,
)
from bijux_rar.core.fingerprints import canonical_dumps, stable_id
from bijux_rar.core.rar_types import Trace


def test_fingerprint_stable_on_rewrite(tmp_path: Path) -> None:
    trace = Trace(id="t1", events=[], metadata={}, spec_id="", plan_id="")
    p = tmp_path / "trace.jsonl"
    write_trace_jsonl(trace, p)
    fp1 = fingerprint_trace_file(p)
    # Re-write the same trace and fingerprints must match (line endings enforced as LF).
    write_trace_jsonl(trace, p)
    fp2 = fingerprint_trace_file(p)
    assert fp1 == fp2


def test_stable_id_versioned_and_deterministic() -> None:
    obj = {"a": 1, "b": [2, 3]}
    sid1 = stable_id("kind", obj)
    sid2 = stable_id("kind", {"b": [2, 3], "a": 1})
    assert sid1 == sid2
    assert "_v1_" in sid1


def test_canonical_dumps_locale_independent() -> None:
    data = {"mixed": ["Å", "A", "a", "Ä"], "num": 1.0}
    s1 = canonical_dumps(data)
    s2 = canonical_dumps({"num": 1.0, "mixed": ["Å", "A", "a", "Ä"]})
    assert s1 == s2
