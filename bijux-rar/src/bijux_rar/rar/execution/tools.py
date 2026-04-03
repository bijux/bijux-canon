# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Protocol, cast

from bijux_rar.core.fingerprints import canonical_dumps, stable_id
from bijux_rar.core.rar_types import JsonValue, ToolCall, ToolDescriptor, ToolResult
from bijux_rar.rar.retrieval.chunked_bm25 import SCHEMA_VERSION as BM25_SCHEMA_VERSION
from bijux_rar.rar.retrieval.chunked_bm25 import build_or_load_index
from bijux_rar.rar.retrieval.corpus import load_corpus_jsonl


class Tool(Protocol):
    def invoke(self, *, arguments: dict[str, JsonValue], seed: int) -> JsonValue: ...


@dataclass(frozen=True)
class ToolRegistry:
    tools: Mapping[str, Tool]

    def describe(self) -> list[ToolDescriptor]:
        out: list[ToolDescriptor] = []
        for name, tool in sorted(self.tools.items()):
            version = getattr(tool, "version", "0.0.0")
            cfg = getattr(tool, "config_fingerprint", "unknown")
            out.append(
                ToolDescriptor(
                    name=name, version=str(version), config_fingerprint=str(cfg)
                )
            )
        return out

    def invoke(self, call: ToolCall, *, seed: int) -> ToolResult:
        tool = self.tools[call.tool_name]
        try:
            result = tool.invoke(arguments=call.arguments, seed=seed)
            return ToolResult(call_id=call.id, success=True, result=result)
        except Exception as e:  # noqa: BLE001
            return ToolResult(call_id=call.id, success=False, error=str(e), result=None)


@dataclass(frozen=True)
class FrozenToolRegistry:
    """Deterministic playback: no tool execution, only recorded outputs."""

    recorded: Mapping[str, ToolResult]
    descriptors: list[ToolDescriptor]

    def describe(self) -> list[ToolDescriptor]:
        return list(self.descriptors)

    def invoke(self, call: ToolCall, *, seed: int) -> ToolResult:  # noqa: ARG002
        try:
            return self.recorded[call.id]
        except KeyError as e:
            raise KeyError(f"Missing recorded ToolResult for call_id={call.id}") from e


@dataclass(frozen=True)
class FakeTool:
    name: str
    version: str = "0.0.0"

    @property
    def config_fingerprint(self) -> str:
        return stable_id("toolcfg", {"name": self.name})

    def invoke(self, *, arguments: dict[str, JsonValue], seed: int) -> JsonValue:
        if self.name == "retrieve":
            q = str(arguments.get("query", ""))
            raw_top_k = arguments.get("top_k", 3)
            top_k = int(raw_top_k) if isinstance(raw_top_k, (int, float, str)) else 3
            evidences: list[dict[str, JsonValue]] = []
            for i in range(top_k):
                text = f"EVIDENCE[{i}] for '{q}' (seed={seed})"
                chunk_bytes = text.encode("utf-8")
                cid = hashlib.sha256(chunk_bytes).hexdigest()
                evidences.append(
                    {
                        "uri": f"mem://{q}/{i}",
                        "text": text,
                        "span": [0, len(chunk_bytes)],
                        "chunk_span": [0, len(chunk_bytes)],
                        "chunk_id": cid,
                        "chunk_sha256": hashlib.sha256(chunk_bytes).hexdigest(),
                    }
                )
            return {"evidences": cast(JsonValue, evidences)}

        return {"echo": arguments, "seed": seed}


@dataclass
class BM25Retriever:
    """Deterministic local retriever over a JSONL corpus.

    Upgraded to:
      - chunk-level evidence with stable chunk ids and byte spans
      - persisted BM25 index pinned under run provenance
      - provenance fingerprints returned in tool output
    """

    corpus_path: Path
    artifacts_dir: Path | None = None
    chunk_chars: int = 800
    overlap_chars: int = 120
    k1: float = 1.2
    b: float = 0.75
    version: str = "2.0.0"
    corpus_max_bytes: int | None = None
    max_chunks: int | None = None
    lazy_index: bool = False
    max_docs: int | None = None
    parallel_scoring: bool = False

    _index_sha: str | None = None
    _corpus_sha: str | None = None
    _index = None
    _docs = None

    def __post_init__(self) -> None:
        if not self.corpus_path.exists():
            raise FileNotFoundError(self.corpus_path)

    @property
    def _corpus_sha256(self) -> str:
        if self._corpus_sha is None:
            # Always hash the pinned snapshot if artifacts_dir is set.
            corpus_src = self._pin_corpus() if self.artifacts_dir else self.corpus_path
            self._corpus_sha = hashlib.sha256(corpus_src.read_bytes()).hexdigest()
        return self._corpus_sha

    @property
    def config_fingerprint(self) -> str:
        return stable_id(
            "toolcfg",
            {
                "name": "retrieve",
                "backend": "bm25-chunked",
                "corpus_sha256": self._corpus_sha256,
                "chunk_chars": self.chunk_chars,
                "overlap_chars": self.overlap_chars,
                "k1": self.k1,
                "b": self.b,
                "schema_version": BM25_SCHEMA_VERSION,
                "max_chunks": self.max_chunks,
                "max_docs": self.max_docs,
                "parallel_scoring": self.parallel_scoring,
                "lazy_index": self.lazy_index,
                "corpus_max_bytes": self.corpus_max_bytes,
            },
        )

    def _pin_corpus(self) -> Path:
        if self.artifacts_dir is None:
            return self.corpus_path
        pinned = self.artifacts_dir / "provenance" / "corpus.jsonl"
        pinned.parent.mkdir(parents=True, exist_ok=True)
        if not pinned.exists():
            pinned.write_bytes(self.corpus_path.read_bytes())
        return pinned

    def _load_index(self) -> None:
        pinned_corpus = self._pin_corpus()
        if self.artifacts_dir is not None:
            index_path = self.artifacts_dir / "provenance" / "index" / "bm25_index.json"
        else:
            index_path = self.corpus_path.with_suffix(".bm25_index.json")
        idx, corpus_sha, idx_sha = build_or_load_index(
            corpus_path=pinned_corpus,
            index_path=None if self.lazy_index else index_path,
            chunk_chars=self.chunk_chars,
            overlap_chars=self.overlap_chars,
            corpus_max_bytes=self.corpus_max_bytes,
            max_chunks=self.max_chunks,
            max_docs=self.max_docs,
        )
        self._index = idx
        self._index_sha = idx_sha
        self._corpus_sha = corpus_sha
        self._docs = tuple(load_corpus_jsonl(pinned_corpus))

    def invoke(self, *, arguments: dict[str, JsonValue], seed: int) -> JsonValue:  # noqa: ARG002
        q = str(arguments.get("query", ""))
        raw_top_k = arguments.get("top_k", 3)
        top_k = int(raw_top_k) if isinstance(raw_top_k, (int, float, str)) else 3

        if self._index is None:
            self._load_index()
        if self._index is None or self._docs is None:
            raise RuntimeError("BM25Retriever not initialized")

        ranked = self._index.top_k(
            q, k=top_k, k1=self.k1, b=self.b, parallel=self.parallel_scoring
        )
        evidences: list[dict[str, JsonValue]] = []
        doc_meta = {d.doc_id: d for d in self._docs}

        for chunk, score in ranked:
            meta = doc_meta.get(chunk.doc_id)
            evidences.append(
                {
                    "uri": f"corpus://{chunk.doc_id}#{chunk.start_byte}-{chunk.end_byte}",
                    "doc_id": chunk.doc_id,
                    "chunk_id": chunk.chunk_id,
                    "score": float(score),
                    "text": chunk.text,
                    "span": [chunk.start_byte, chunk.end_byte],
                    "chunk_span": [chunk.start_byte, chunk.end_byte],
                    "chunk_sha256": hashlib.sha256(
                        chunk.text.encode("utf-8")
                    ).hexdigest(),
                    "doc_sha256": chunk.doc_sha256,
                    "title": meta.title if meta else None,
                    "source": meta.source if meta else None,
                }
            )

        provenance: dict[str, JsonValue] = {
            "schema_version": BM25_SCHEMA_VERSION,
            "corpus_sha256": self._index.corpus_sha256,
            "chunk_chars": self.chunk_chars,
            "overlap_chars": self.overlap_chars,
            "k1": self.k1,
            "b": self.b,
            "index_sha256": self._index_sha,
            "tokenizer": "unicode_word",
            "max_chunks": self.max_chunks,
            "max_docs": self.max_docs,
            "parallel_scoring": self.parallel_scoring,
            "lazy_index": self.lazy_index,
            "corpus_max_bytes": self.corpus_max_bytes,
        }
        cfg_hash = hashlib.sha256(
            canonical_dumps(
                {
                    "chunk_chars": self.chunk_chars,
                    "overlap_chars": self.overlap_chars,
                    "k1": self.k1,
                    "b": self.b,
                    "tokenizer": "unicode_word",
                    "max_chunks": self.max_chunks,
                    "max_docs": self.max_docs,
                    "parallel_scoring": self.parallel_scoring,
                    "lazy_index": self.lazy_index,
                    "corpus_max_bytes": self.corpus_max_bytes,
                }
            ).encode("utf-8")
        ).hexdigest()
        provenance["config_sha256"] = cfg_hash
        if self.artifacts_dir is not None:
            corpus_rel = (
                (self.artifacts_dir / "provenance" / "corpus.jsonl")
                .relative_to(self.artifacts_dir)
                .as_posix()
            )
            index_rel = (
                (self.artifacts_dir / "provenance" / "index" / "bm25_index.json")
                .relative_to(self.artifacts_dir)
                .as_posix()
            )
            provenance["corpus_path"] = corpus_rel
            provenance["index_path"] = index_rel
            chunks_path = self.artifacts_dir / "provenance" / "chunks.jsonl"
            chunks_path.parent.mkdir(parents=True, exist_ok=True)
            if not chunks_path.exists():
                with chunks_path.open("w", encoding="utf-8", newline="") as fh:
                    for ch in self._index.chunks:
                        fh.write(
                            canonical_dumps(
                                {
                                    "chunk_id": ch.chunk_id,
                                    "doc_id": ch.doc_id,
                                    "start_byte": ch.start_byte,
                                    "end_byte": ch.end_byte,
                                    "chunk_sha256": hashlib.sha256(
                                        ch.text.encode("utf-8")
                                    ).hexdigest(),
                                    "doc_sha256": ch.doc_sha256,
                                }
                            )
                            + "\n"
                        )
            provenance["chunks_path"] = chunks_path.relative_to(
                self.artifacts_dir
            ).as_posix()
            prov_file = self.artifacts_dir / "provenance" / "retrieval_provenance.json"
            if not prov_file.exists():
                prov_file.parent.mkdir(parents=True, exist_ok=True)
                prov_file.write_text(
                    canonical_dumps(provenance) + "\n", encoding="utf-8"
                )
        else:
            provenance["corpus_path"] = str(self.corpus_path)
        return {"evidences": cast(JsonValue, evidences), "provenance": provenance}
