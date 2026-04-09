# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Tool runtime helpers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Protocol, cast

from bijux_canon_reason.core.fingerprints import canonical_dumps, stable_id
from bijux_canon_reason.core.types import (
    JsonValue,
    ToolCall,
    ToolDescriptor,
    ToolResult,
)
from bijux_canon_reason.retrieval.chunked_bm25 import (
    SCHEMA_VERSION as BM25_SCHEMA_VERSION,
)
from bijux_canon_reason.retrieval.chunked_bm25 import (
    ChunkedBM25Index,
    build_or_load_index,
)
from bijux_canon_reason.retrieval.chunking import Chunk
from bijux_canon_reason.retrieval.corpus import CorpusDoc, load_corpus_jsonl


class Tool(Protocol):
    """Represents tool."""
    def invoke(self, *, arguments: dict[str, JsonValue], seed: int) -> JsonValue:
        """Invoke the tool with the provided arguments."""

        ...


@dataclass(frozen=True)
class ToolRegistry:
    """Represents tool registry."""
    tools: Mapping[str, Tool]

    def describe(self) -> list[ToolDescriptor]:
        """Describe the current object."""
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
        """Invoke the requested operation."""
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
        """Describe the current object."""
        return list(self.descriptors)

    def invoke(self, call: ToolCall, *, seed: int) -> ToolResult:  # noqa: ARG002
        """Invoke the requested operation."""
        try:
            return self.recorded[call.id]
        except KeyError as e:
            raise KeyError(f"Missing recorded ToolResult for call_id={call.id}") from e


@dataclass(frozen=True)
class FakeTool:
    """Represents fake tool."""
    name: str
    version: str = "0.0.0"

    @property
    def config_fingerprint(self) -> str:
        """Handle config fingerprint."""
        return stable_id("toolcfg", {"name": self.name})

    def invoke(self, *, arguments: dict[str, JsonValue], seed: int) -> JsonValue:
        """Invoke the requested operation."""
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


@dataclass(frozen=True)
class _ProvenancePaths:
    """Represents provenance paths."""
    root: Path
    corpus_path: Path
    index_path: Path
    chunks_path: Path
    retrieval_path: Path


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
        """Finalize initialization after dataclass construction."""
        if not self.corpus_path.exists():
            raise FileNotFoundError(self.corpus_path)

    @property
    def _corpus_sha256(self) -> str:
        """Handle corpus sha256."""
        if self._corpus_sha is None:
            # Always hash the pinned snapshot if artifacts_dir is set.
            corpus_src = self._pin_corpus() if self.artifacts_dir else self.corpus_path
            self._corpus_sha = hashlib.sha256(corpus_src.read_bytes()).hexdigest()
        return self._corpus_sha

    @property
    def config_fingerprint(self) -> str:
        """Handle config fingerprint."""
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
        """Handle pin corpus."""
        if self.artifacts_dir is None:
            return self.corpus_path
        paths = _provenance_paths(self.artifacts_dir)
        paths.root.mkdir(parents=True, exist_ok=True)
        if not paths.corpus_path.exists():
            paths.corpus_path.write_bytes(self.corpus_path.read_bytes())
        return paths.corpus_path

    def _load_index(self) -> None:
        """Load index."""
        pinned_corpus = self._pin_corpus()
        index_path = _index_path(self.artifacts_dir, self.corpus_path)
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
        """Invoke the requested operation."""
        q = str(arguments.get("query", ""))
        raw_top_k = arguments.get("top_k", 3)
        top_k = int(raw_top_k) if isinstance(raw_top_k, (int, float, str)) else 3

        index, docs = self._require_loaded_index()

        ranked = index.top_k(
            q, k=top_k, k1=self.k1, b=self.b, parallel=self.parallel_scoring
        )
        doc_meta = {d.doc_id: d for d in docs}
        evidences = _build_retrieved_evidences(ranked=ranked, doc_meta=doc_meta)
        provenance = self._build_retrieval_provenance(index)
        self._persist_retrieval_provenance(provenance)
        return {"evidences": cast(JsonValue, evidences), "provenance": provenance}

    def _require_loaded_index(self) -> tuple[ChunkedBM25Index, tuple[CorpusDoc, ...]]:
        """Require loaded index."""
        if self._index is None:
            self._load_index()
        if self._index is None or self._docs is None:
            raise RuntimeError("BM25Retriever not initialized")
        return cast(ChunkedBM25Index, self._index), self._docs

    def _build_retrieval_provenance(
        self, index: ChunkedBM25Index
    ) -> dict[str, JsonValue]:
        """Build retrieval provenance."""
        provenance: dict[str, JsonValue] = {
            "schema_version": BM25_SCHEMA_VERSION,
            "corpus_sha256": index.corpus_sha256,
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
            "config_sha256": _config_sha256(
                chunk_chars=self.chunk_chars,
                overlap_chars=self.overlap_chars,
                k1=self.k1,
                b=self.b,
                max_chunks=self.max_chunks,
                max_docs=self.max_docs,
                parallel_scoring=self.parallel_scoring,
                lazy_index=self.lazy_index,
                corpus_max_bytes=self.corpus_max_bytes,
            ),
        }
        if self.artifacts_dir is None:
            provenance["corpus_path"] = str(self.corpus_path)
            return provenance

        paths = _provenance_paths(self.artifacts_dir)
        provenance["corpus_path"] = paths.corpus_path.relative_to(
            self.artifacts_dir
        ).as_posix()
        provenance["index_path"] = paths.index_path.relative_to(
            self.artifacts_dir
        ).as_posix()
        provenance["chunks_path"] = _write_chunk_manifest(
            artifacts_dir=self.artifacts_dir,
            chunks_path=paths.chunks_path,
            chunks=index.chunks,
        )
        return provenance

    def _persist_retrieval_provenance(self, provenance: dict[str, JsonValue]) -> None:
        """Handle persist retrieval provenance."""
        if self.artifacts_dir is None:
            return

        paths = _provenance_paths(self.artifacts_dir)
        if paths.retrieval_path.exists():
            return
        paths.root.mkdir(parents=True, exist_ok=True)
        paths.retrieval_path.write_text(
            canonical_dumps(provenance) + "\n",
            encoding="utf-8",
        )


def _build_retrieved_evidences(
    *,
    ranked: list[tuple[Chunk, float]],
    doc_meta: dict[str, CorpusDoc],
) -> list[dict[str, JsonValue]]:
    """Build retrieved evidences."""
    evidences: list[dict[str, JsonValue]] = []
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
                "chunk_sha256": hashlib.sha256(chunk.text.encode("utf-8")).hexdigest(),
                "doc_sha256": chunk.doc_sha256,
                "title": meta.title if meta else None,
                "source": meta.source if meta else None,
            }
        )
    return evidences


def _config_sha256(
    *,
    chunk_chars: int,
    overlap_chars: int,
    k1: float,
    b: float,
    max_chunks: int | None,
    max_docs: int | None,
    parallel_scoring: bool,
    lazy_index: bool,
    corpus_max_bytes: int | None,
) -> str:
    """Handle config sha256."""
    payload = {
        "chunk_chars": chunk_chars,
        "overlap_chars": overlap_chars,
        "k1": k1,
        "b": b,
        "tokenizer": "unicode_word",
        "max_chunks": max_chunks,
        "max_docs": max_docs,
        "parallel_scoring": parallel_scoring,
        "lazy_index": lazy_index,
        "corpus_max_bytes": corpus_max_bytes,
    }
    return hashlib.sha256(canonical_dumps(payload).encode("utf-8")).hexdigest()


def _provenance_paths(artifacts_dir: Path) -> _ProvenancePaths:
    """Handle provenance paths."""
    root = artifacts_dir / "provenance"
    return _ProvenancePaths(
        root=root,
        corpus_path=root / "corpus.jsonl",
        index_path=root / "index" / "bm25_index.json",
        chunks_path=root / "chunks.jsonl",
        retrieval_path=root / "retrieval_provenance.json",
    )


def _index_path(artifacts_dir: Path | None, corpus_path: Path) -> Path:
    """Handle index path."""
    if artifacts_dir is None:
        return corpus_path.with_suffix(".bm25_index.json")
    return _provenance_paths(artifacts_dir).index_path


def _write_chunk_manifest(
    *,
    artifacts_dir: Path,
    chunks_path: Path,
    chunks: tuple[Chunk, ...],
) -> str:
    """Write chunk manifest."""
    chunks_path.parent.mkdir(parents=True, exist_ok=True)
    if not chunks_path.exists():
        with chunks_path.open("w", encoding="utf-8", newline="") as fh:
            for chunk in chunks:
                fh.write(
                    canonical_dumps(
                        {
                            "chunk_id": chunk.chunk_id,
                            "doc_id": chunk.doc_id,
                            "start_byte": chunk.start_byte,
                            "end_byte": chunk.end_byte,
                            "chunk_sha256": hashlib.sha256(
                                chunk.text.encode("utf-8")
                            ).hexdigest(),
                            "doc_sha256": chunk.doc_sha256,
                        }
                    )
                    + "\n"
                )
    return chunks_path.relative_to(artifacts_dir).as_posix()
