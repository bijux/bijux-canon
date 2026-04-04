# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Rendering and file-output helpers for pipeline-mode CLI commands."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bijux_canon_ingest.result.types import ErrInfo, Ok, Result


def render_error(result: Result[Any, ErrInfo]) -> int:
    """Render a pipeline command error payload to stdout."""

    if isinstance(result, Ok):
        return 0
    error = result.error
    print(
        json.dumps(
            {"error": {"code": error.code, "msg": error.msg, "stage": error.stage}},
            ensure_ascii=False,
        )
    )
    return 2 if error.code.startswith("PARSE") else 1


def chunk_to_json(chunk: Any) -> dict[str, Any]:
    """Project a chunk-like value to the stable JSON payload used by the CLI."""

    if hasattr(chunk, "metadata"):
        metadata = chunk.metadata
        try:
            metadata = dict(metadata)
        except Exception:
            metadata = {}
    else:
        metadata = {}
    return {
        "doc_id": getattr(chunk, "doc_id", ""),
        "text": getattr(chunk, "text", ""),
        "start": getattr(chunk, "start", 0),
        "end": getattr(chunk, "end", 0),
        "metadata": metadata,
        "embedding": list(getattr(chunk, "embedding", ())),
    }


def write_chunk_results(results: list[Result[Any, ErrInfo]], *, out_path: Path) -> None:
    """Write successful chunk results as JSONL."""

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        for result in results:
            if isinstance(result, Ok):
                handle.write(
                    json.dumps(chunk_to_json(result.value), ensure_ascii=False)
                )
                handle.write("\n")


__all__ = ["chunk_to_json", "render_error", "write_chunk_results"]
