# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from pathlib import Path

from bijux_rar.boundaries.serde.trace_jsonl import read_trace_jsonl, write_trace_jsonl
from bijux_rar.core.rar_types import Trace


def test_trace_jsonl_writer_uses_lf_only(tmp_path: Path) -> None:
    p = tmp_path / "trace.jsonl"
    t = Trace(events=[]).with_content_id()
    write_trace_jsonl(t, p)
    b = p.read_bytes()
    assert b"\r\n" not in b


def test_trace_jsonl_reader_tolerates_crlf(tmp_path: Path) -> None:
    p = tmp_path / "trace.jsonl"
    t = Trace(events=[]).with_content_id()
    write_trace_jsonl(t, p)

    # Convert to CRLF and ensure it still loads.
    crlf = p.read_text(encoding="utf-8").replace("\n", "\r\n")
    p.write_text(crlf, encoding="utf-8", newline="")

    out = read_trace_jsonl(p)
    assert out.schema_version == t.schema_version
    assert out.runtime_protocol_version == t.runtime_protocol_version
