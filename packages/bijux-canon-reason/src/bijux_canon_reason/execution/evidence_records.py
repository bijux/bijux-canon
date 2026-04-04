# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

import hashlib
from pathlib import Path

from bijux_canon_reason.core.fingerprints import stable_id
from bijux_canon_reason.core.types import EvidenceRef, JsonValue
from bijux_canon_reason.execution.runtime import ExecutionRuntime


def coerce_reasoner_value(value: object) -> JsonValue:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, dict)):
        return value
    return str(value)


def write_evidence_record(
    runtime: ExecutionRuntime,
    *,
    uri: str,
    content: bytes,
    span: tuple[int, int],
    chunk_id: str,
) -> EvidenceRef:
    sha = _sha256_bytes(content)
    if runtime.artifacts_dir is None:
        return EvidenceRef(
            uri=uri,
            sha256=sha,
            span=span,
            chunk_id=chunk_id,
            content_path="",
        ).with_content_id()

    evidence_id = stable_id(
        "ev",
        {"uri": uri, "sha256": sha, "span": span, "chunk_id": chunk_id},
    )
    rel_path = Path("evidence") / f"{evidence_id}.txt"
    abs_path = runtime.artifacts_dir / rel_path
    _ensure_dir(abs_path.parent)
    tmp_path = abs_path.with_suffix(".tmp")
    tmp_path.write_bytes(content)
    tmp_path.replace(abs_path)
    return EvidenceRef(
        id=evidence_id,
        uri=uri,
        sha256=sha,
        span=span,
        chunk_id=chunk_id,
        content_path=rel_path.as_posix(),
    )


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


__all__ = ["coerce_reasoner_value", "write_evidence_record"]
