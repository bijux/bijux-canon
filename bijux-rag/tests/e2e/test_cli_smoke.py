# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import json
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from bijux_rag.boundaries.shells.cli import main as cli_main

doc_strategy = st.builds(
    lambda doc_id, title, abstract, categories: {
        "doc_id": doc_id,
        "title": title,
        "abstract": abstract,
        "categories": categories,
    },
    doc_id=st.from_regex(r"[a-z0-9\-]{3,8}", fullmatch=True),
    title=st.text(min_size=5, max_size=40),
    abstract=st.text(min_size=32, max_size=512),
    categories=st.sampled_from(["cs.CL", "cs.AI", "cs.LG"]),
)


def _write_csv(tmp_path: Path, docs: list[dict[str, str]]) -> Path:
    path = tmp_path / "docs.csv"
    path.write_text("doc_id,title,abstract,categories\n", encoding="utf-8")
    with path.open("a", encoding="utf-8") as f:
        for row in docs:
            safe_title = row["title"].replace('"', "'")
            safe_abs = row["abstract"].replace('"', "'").replace("\n", " ")
            f.write(f'{row["doc_id"]},"{safe_title}","{safe_abs}",{row["categories"]}\n')
    return path


def _write_config(tmp_path: Path, chunk_size: int, overlap: int, tail: str) -> Path:
    cfg = {
        "steps": [
            {"name": "clean", "params": {}},
            {
                "name": "chunk",
                "params": {"chunk_size": chunk_size, "overlap": overlap, "tail_policy": tail},
            },
            {"name": "embed", "params": {}},
        ]
    }
    path = tmp_path / "pipeline.json"
    path.write_text(json.dumps(cfg), encoding="utf-8")
    return path


@pytest.mark.e2e
@pytest.mark.timeout(0)
@given(
    docs=st.lists(doc_strategy, min_size=1, max_size=3),
    chunk_size=st.integers(min_value=32, max_value=192),
    overlap=st.integers(min_value=0, max_value=32),
    tail=st.sampled_from(["emit_short", "drop", "pad"]),
)
@settings(
    max_examples=250, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
def test_cli_end_to_end_chunks(
    tmp_path: Path, docs: list[dict[str, str]], chunk_size: int, overlap: int, tail: str
) -> None:
    if overlap >= chunk_size:
        overlap = chunk_size // 2
    if tail == "drop" and any(len(d["abstract"]) <= chunk_size for d in docs):
        tail = "emit_short"

    input_csv = _write_csv(tmp_path, docs)
    cfg_path = _write_config(tmp_path, chunk_size, overlap, tail)
    out_path = tmp_path / "chunks.jsonl"

    exit_code = cli_main([str(input_csv), "--config", str(cfg_path), "--out", str(out_path)])
    assert exit_code == 0
    assert out_path.exists()

    lines = [
        json.loads(line)
        for line in out_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert lines, "expected at least one chunk"

    for chunk in lines:
        assert "embedding" in chunk and len(chunk["embedding"]) == 16
        assert 0 <= chunk["start"] <= chunk["end"]
        assert chunk["doc_id"] in {d["doc_id"] for d in docs}
        assert len(chunk["text"]) <= chunk_size + overlap


@pytest.mark.e2e
@pytest.mark.timeout(0)
@given(
    docs=st.lists(doc_strategy, min_size=1, max_size=2),
    chunk_size=st.integers(min_value=48, max_value=160),
    overlap=st.integers(min_value=0, max_value=24),
)
@settings(
    max_examples=250, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
def test_cli_overrides_apply(
    tmp_path: Path, docs: list[dict[str, str]], chunk_size: int, overlap: int
) -> None:
    if overlap >= chunk_size:
        overlap = max(0, chunk_size // 4)
    if any(len(d["abstract"]) <= chunk_size for d in docs):
        chunk_size = min(
            chunk_size, max(len(max(docs, key=lambda x: len(x["abstract"]))["abstract"]), 48)
        )
    if overlap >= chunk_size:
        overlap = max(0, chunk_size // 4)

    input_csv = _write_csv(tmp_path, docs)
    cfg_path = _write_config(tmp_path, 128, 0, "emit_short")
    out_path = tmp_path / "chunks.jsonl"

    exit_code = cli_main(
        [
            str(input_csv),
            "--config",
            str(cfg_path),
            "--set",
            f"chunk.chunk_size={chunk_size}",
            "--set",
            f"chunk.overlap={overlap}",
            "--out",
            str(out_path),
        ]
    )
    assert exit_code == 0

    lines = [
        json.loads(line)
        for line in out_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert lines
    # verify that at least one chunk reflects the override (no chunk should exceed override chunk_size + overlap)
    assert all(len(c["text"]) <= chunk_size + overlap for c in lines)
