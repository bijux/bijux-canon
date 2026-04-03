# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from collections.abc import Iterator
import os
from pathlib import Path
import tempfile

from pydantic import TypeAdapter

from bijux_rar.boundaries.serde.json_canonical import canonical_json_line
from bijux_rar.core.fingerprints import fingerprint_bytes
from bijux_rar.core.rar_types import Trace, TraceEvent

_TRACE_HEADER_RECORD = "trace_header"
_TRACE_EVENT_RECORD = "trace_event"


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=path.parent, prefix=path.name, suffix=".tmp", delete=False
    ) as tmp:
        tmp.write(data)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def write_trace_jsonl(trace: Trace, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    header = {
        "record": _TRACE_HEADER_RECORD,
        "id": trace.id,
        "metadata": trace.metadata,
        "spec_id": trace.spec_id,
        "plan_id": trace.plan_id,
        "runtime_protocol_version": getattr(trace, "runtime_protocol_version", 1),
        "schema_version": trace.schema_version,
        "fingerprint_algo": trace.fingerprint_algo,
        "canonicalization_version": trace.canonicalization_version,
    }

    lines = [canonical_json_line(header) + "\n"]
    for ev in trace.events:
        rec = {
            "record": _TRACE_EVENT_RECORD,
            "event": ev.model_dump(mode="json"),
        }
        lines.append(canonical_json_line(rec) + "\n")
    # Force stable newlines across platforms (\n), otherwise fingerprints diverge.
    payload = "".join(lines).encode("utf-8")
    _atomic_write(path, payload)


def _iter_lines(path: Path) -> Iterator[str]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            # Tolerate Windows CRLF while keeping stable canonical content.
            s = line.rstrip("\r\n")
            if not s:
                continue
            yield s


def read_trace_jsonl(path: Path) -> Trace:
    import json

    it = _iter_lines(path)
    first = next(it, None)
    if first is None:
        raise ValueError("Empty trace jsonl.")

    header = json.loads(first)
    if header.get("record") != _TRACE_HEADER_RECORD:
        raise ValueError("First JSONL record must be trace_header.")

    events: list[TraceEvent] = []
    adapter: TypeAdapter[TraceEvent] = TypeAdapter(TraceEvent)
    for line in it:
        rec = json.loads(line)
        if rec.get("record") != _TRACE_EVENT_RECORD:
            raise ValueError("Unexpected JSONL record type.")
        events.append(adapter.validate_python(rec["event"]))

    return Trace.model_validate(
        {
            "id": header.get("id"),
            "metadata": header.get("metadata", {}),
            "spec_id": header.get("spec_id"),
            "plan_id": header.get("plan_id"),
            "runtime_protocol_version": header.get("runtime_protocol_version", 1),
            "schema_version": header.get("schema_version"),
            "fingerprint_algo": header.get("fingerprint_algo", "sha256"),
            "canonicalization_version": header.get("canonicalization_version", 1),
            "events": [e.model_dump(mode="json") for e in events],
        }
    )


def fingerprint_trace_file(path: Path) -> str:
    return fingerprint_bytes(path.read_bytes())
