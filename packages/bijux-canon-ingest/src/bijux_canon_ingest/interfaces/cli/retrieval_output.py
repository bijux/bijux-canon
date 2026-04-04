# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Output rendering helpers for retrieval-oriented CLI commands."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from bijux_canon_ingest.retrieval.ports import Answer, Candidate


class YamlModule(Protocol):
    def safe_dump(
        self,
        data: object,
        *,
        sort_keys: bool = ...,
        allow_unicode: bool = ...,
    ) -> str: ...


def render_retrieve_output(candidates: list[Candidate]) -> str:
    payload = {
        "candidates": [
            {
                "doc_id": candidate.chunk.doc_id,
                "chunk_id": candidate.chunk.chunk_id,
                "text": candidate.chunk.text,
                "start": candidate.chunk.start,
                "end": candidate.chunk.end,
                "metadata": dict(candidate.chunk.metadata),
                "score": float(candidate.score),
            }
            for candidate in candidates
        ]
    }
    return json.dumps(payload, ensure_ascii=False)


def render_answer_output(
    answer: Answer,
    *,
    output_format: str,
    yaml_module: YamlModule | None = None,
) -> str:
    payload: dict[str, object] = {
        "text": answer.text,
        "citations": [
            {
                "doc_id": citation.doc_id,
                "chunk_id": citation.chunk_id,
                "start": citation.start,
                "end": citation.end,
            }
            for citation in answer.citations
        ],
    }
    if output_format == "yaml":
        if yaml_module is None:
            raise ValueError("yaml_module is required for YAML output")
        return yaml_module.safe_dump(payload, sort_keys=False, allow_unicode=True)
    return json.dumps(payload, ensure_ascii=False)


def write_output(*, payload: str, out_path: Path | None) -> int:
    if out_path is None:
        print(payload)
        return 0
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        payload + ("" if payload.endswith("\n") else "\n"), encoding="utf-8"
    )
    return 0


__all__ = ["YamlModule", "render_answer_output", "render_retrieve_output", "write_output"]
