# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from pathlib import Path

import pytest

from bijux_rar.core.rar_types import Trace
from bijux_rar.rar.traces.replay import replay_from_artifacts
from bijux_rar.boundaries.serde.trace_jsonl import write_trace_jsonl


def test_replay_missing_spec_raises(tmp_path: Path) -> None:
    trace = Trace(spec_id="s", plan_id="p", events=[], metadata={}).with_content_id()
    trace_path = tmp_path / "trace.jsonl"
    write_trace_jsonl(trace, trace_path)
    with pytest.raises(FileNotFoundError):
        replay_from_artifacts(trace_path)


def test_replay_provenance_mismatch(tmp_path: Path) -> None:
    # create minimal run dir with spec/meta/provenance but mismatch hashes
    run_dir = tmp_path
    trace = Trace(spec_id="s", plan_id="p", events=[], metadata={"retrieval_provenance": {"corpus_sha256": "x", "index_sha256": "y"}}).with_content_id()
    trace_path = run_dir / "trace.jsonl"
    write_trace_jsonl(trace, trace_path)
    (run_dir / "spec.json").write_text('{"description":"q","constraints":{}}', encoding="utf-8")
    # minimal plan required by replay
    (run_dir / "plan.json").write_text('{"spec_id":"s","nodes":[],"edges":[]}', encoding="utf-8")
    (run_dir / "run_meta.json").write_text('{"preset":"default","seed":0}', encoding="utf-8")
    prov_dir = run_dir / "provenance"
    prov_dir.mkdir(parents=True, exist_ok=True)
    corpus = prov_dir / "corpus.jsonl"
    corpus.write_text("{}", encoding="utf-8")
    index = prov_dir / "index" / "bm25_index.json"
    index.parent.mkdir(parents=True, exist_ok=True)
    index.write_text("{}", encoding="utf-8")
    (prov_dir / "retrieval_provenance.json").write_text('{"corpus_sha256":"a","index_sha256":"b"}', encoding="utf-8")
    with pytest.raises(ValueError):
        replay_from_artifacts(trace_path)
