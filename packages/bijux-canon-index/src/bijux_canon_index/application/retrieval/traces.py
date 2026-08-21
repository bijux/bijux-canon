# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Immutable retrieval traces with restart-safe inspection and replay."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from enum import Enum
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
from types import MappingProxyType
from typing import cast

from .dense import DenseCandidateBatch, DenseCandidateMode
from .fusion import RrfFusionBatch
from .lexical import LexicalCandidateBatch
from .locators import CitationResolutionBatch, CitationRetrievalMode
from .reranking import RerankBatch
from .selection import EvidenceSelectionBatch

_ARTIFACT_ID = re.compile(r"^sha256:([0-9a-f]{64})$")


def _json_value(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_value(item) for item in value]
    return value


def _canonical_json(value: object) -> str:
    return json.dumps(
        _json_value(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha256_json(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _canonical_mapping(value: Mapping[str, object]) -> dict[str, object]:
    normalized = json.loads(_canonical_json(value))
    if not isinstance(normalized, dict):
        raise ValueError("retrieval trace sections must be JSON objects")
    return cast(dict[str, object], normalized)


def _freeze(value: object) -> object:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {str(key): _freeze(item) for key, item in value.items()}
        )
    if isinstance(value, list | tuple):
        return tuple(_freeze(item) for item in value)
    return value


class RetrievalTraceReplayOutcome(str, Enum):
    """Whether a replay retained immutable inputs and semantic outputs."""

    exact_match = "exact_match"
    diverged = "diverged"
    refused = "refused"


class RetrievalTraceDriftKind(str, Enum):
    """Immutable retrieval input that changed during replay."""

    request = "request"
    generation = "generation"
    model = "model"
    retrieval_mode = "retrieval_mode"
    filters = "filters"


@dataclass(frozen=True, slots=True)
class RetrievalTraceArtifact:
    """Complete request-to-citation record for one retrieval execution."""

    request: Mapping[str, object]
    generation_id: str
    model_lock_artifact_id: str
    retrieval_mode: CitationRetrievalMode
    filters: Mapping[str, object]
    candidates: Mapping[str, object]
    fusion: Mapping[str, object]
    selection: Mapping[str, object]
    rerank: Mapping[str, object]
    final_hits: tuple[Mapping[str, object], ...]
    timings_ms: Mapping[str, object]
    policy_decisions: Mapping[str, object]
    schema_version: str = "bijux.canon.retrieval.trace.v1"
    execution_id: str = field(init=False)
    artifact_id: str = field(init=False)
    component_hashes: Mapping[str, str] = field(init=False)

    def __post_init__(self) -> None:
        if not self.generation_id or not self.model_lock_artifact_id:
            raise ValueError("retrieval trace requires generation and model identities")
        if not isinstance(self.retrieval_mode, CitationRetrievalMode):
            raise ValueError("retrieval trace mode is unsupported")
        for name, value in self.timings_ms.items():
            if (
                not name
                or isinstance(value, bool)
                or not isinstance(value, int | float)
                or not math.isfinite(float(value))
                or float(value) < 0
            ):
                raise ValueError(
                    "retrieval trace timings must be named finite non-negative values"
                )
        request = _canonical_mapping(self.request)
        filters = _canonical_mapping(self.filters)
        candidates = _canonical_mapping(self.candidates)
        fusion = _canonical_mapping(self.fusion)
        selection = _canonical_mapping(self.selection)
        rerank = _canonical_mapping(self.rerank)
        timings = _canonical_mapping(self.timings_ms)
        decisions = _canonical_mapping(self.policy_decisions)
        hits = tuple(_canonical_mapping(hit) for hit in self.final_hits)
        query_text = request.get("query_text")
        query_hash = request.get("query_text_sha256")
        if not isinstance(query_text, str) or not query_text.strip():
            raise ValueError("retrieval trace request requires non-empty query text")
        if query_hash != hashlib.sha256(query_text.encode("utf-8")).hexdigest():
            raise ValueError("retrieval trace query text identity is invalid")
        if request.get("generation_id") != self.generation_id:
            raise ValueError("retrieval trace request generation identity differs")
        if request.get("retrieval_mode") != self.retrieval_mode.value:
            raise ValueError("retrieval trace request mode differs")
        hit_ranks = tuple(hit.get("rank") for hit in hits)
        if hit_ranks != tuple(range(1, len(hits) + 1)):
            raise ValueError("retrieval trace final hit ranks must be contiguous")
        hit_ids = tuple(hit.get("chunk_id") for hit in hits)
        if any(not isinstance(item, str) or not item for item in hit_ids) or len(
            hit_ids
        ) != len(set(hit_ids)):
            raise ValueError("retrieval trace final chunk identities must be unique")
        object.__setattr__(self, "request", request)
        object.__setattr__(self, "filters", filters)
        object.__setattr__(self, "candidates", candidates)
        object.__setattr__(self, "fusion", fusion)
        object.__setattr__(self, "selection", selection)
        object.__setattr__(self, "rerank", rerank)
        object.__setattr__(self, "timings_ms", timings)
        object.__setattr__(self, "policy_decisions", decisions)
        object.__setattr__(self, "final_hits", hits)
        components = {
            "request": request,
            "filters": filters,
            "candidates": candidates,
            "fusion": fusion,
            "selection": selection,
            "rerank": rerank,
            "final_hits": hits,
            "timings_ms": timings,
            "policy_decisions": decisions,
        }
        object.__setattr__(
            self,
            "component_hashes",
            {name: _sha256_json(value) for name, value in components.items()},
        )
        execution = {
            "filters": filters,
            "generation_id": self.generation_id,
            "model_lock_artifact_id": self.model_lock_artifact_id,
            "request": request,
            "retrieval_mode": self.retrieval_mode.value,
        }
        object.__setattr__(self, "execution_id", f"sha256:{_sha256_json(execution)}")
        object.__setattr__(
            self, "artifact_id", f"sha256:{_sha256_json(self.payload())}"
        )

    def payload(self) -> dict[str, object]:
        """Return canonical artifact content without its derived address."""

        return {
            "artifact_type": "bijux.canon.retrieval.trace",
            "candidates": dict(self.candidates),
            "component_hashes": dict(self.component_hashes),
            "execution_id": self.execution_id,
            "filters": dict(self.filters),
            "final_hits": [dict(hit) for hit in self.final_hits],
            "fusion": dict(self.fusion),
            "generation_id": self.generation_id,
            "model_lock_artifact_id": self.model_lock_artifact_id,
            "policy_decisions": dict(self.policy_decisions),
            "request": dict(self.request),
            "rerank": dict(self.rerank),
            "retrieval_mode": self.retrieval_mode.value,
            "schema_version": self.schema_version,
            "selection": dict(self.selection),
            "timings_ms": dict(self.timings_ms),
        }

    def record(self) -> dict[str, object]:
        """Return the complete stored record."""

        return {"artifact_id": self.artifact_id, **self.payload()}


@dataclass(frozen=True, slots=True)
class StoredRetrievalTrace:
    """Verified bytes and decoded content returned by persistent storage."""

    artifact_id: str
    content_sha256: str
    byte_length: int
    record: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class RetrievalTraceInspection:
    """Content-safe summary of one verified persisted trace."""

    artifact_id: str
    execution_id: str
    generation_id: str
    model_lock_artifact_id: str
    retrieval_mode: str
    final_hit_count: int
    component_hashes: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class RetrievalTraceReplayInput:
    """Recursively immutable inputs recovered from a verified trace."""

    request: Mapping[str, object]
    generation_id: str
    model_lock_artifact_id: str
    retrieval_mode: CitationRetrievalMode
    filters: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class RetrievalTraceReplayComparison:
    """Input-drift and semantic-output comparison for one replay."""

    schema_version: str
    original_artifact_id: str
    replay_artifact_id: str
    original_execution_id: str
    replay_execution_id: str
    outcome: RetrievalTraceReplayOutcome
    drifts: tuple[RetrievalTraceDriftKind, ...]
    changed_components: tuple[str, ...]


RetrievalTraceReplayExecutor = Callable[
    [RetrievalTraceReplayInput], RetrievalTraceArtifact
]


def _expected_dense_mode(mode: CitationRetrievalMode) -> DenseCandidateMode | None:
    if mode in {
        CitationRetrievalMode.dense_exact,
        CitationRetrievalMode.local_hybrid_exact,
    }:
        return DenseCandidateMode.exact
    if mode is CitationRetrievalMode.local_hybrid_ann:
        return DenseCandidateMode.ann
    return None


def _validate_component_identity(
    value: object,
    *,
    generation_id: str,
    query_text_sha256: str,
) -> None:
    if value is None:
        return
    if getattr(value, "generation_id", None) != generation_id:
        raise ValueError("retrieval trace component generation identity differs")
    if getattr(value, "query_text_sha256", None) != query_text_sha256:
        raise ValueError("retrieval trace component query identity differs")


def build_retrieval_trace(
    *,
    request: Mapping[str, object],
    generation_id: str,
    model_lock_artifact_id: str,
    retrieval_mode: CitationRetrievalMode,
    filters: Mapping[str, object],
    citations: CitationResolutionBatch,
    timings_ms: Mapping[str, object],
    lexical: LexicalCandidateBatch | None = None,
    dense: DenseCandidateBatch | None = None,
    fusion: RrfFusionBatch | None = None,
    selection: EvidenceSelectionBatch | None = None,
    rerank: RerankBatch | None = None,
) -> RetrievalTraceArtifact:
    """Build one internally linked trace from canonical retrieval components."""

    query_hash = request.get("query_text_sha256")
    if not isinstance(query_hash, str):
        raise ValueError("retrieval trace request requires a query identity")
    for component in (lexical, dense, fusion, selection, rerank, citations):
        _validate_component_identity(
            component,
            generation_id=generation_id,
            query_text_sha256=query_hash,
        )
    if citations.retrieval_mode is not retrieval_mode:
        raise ValueError("citation result mode differs from retrieval trace")
    if dense is not None and dense.model_lock_artifact_id != model_lock_artifact_id:
        raise ValueError("dense retrieval model identity differs from trace")
    expected_dense = _expected_dense_mode(retrieval_mode)
    if dense is not None and dense.mode is not expected_dense:
        raise ValueError("dense candidate mode differs from retrieval trace")
    if retrieval_mode is CitationRetrievalMode.lexical:
        valid_shape = lexical is not None and dense is None and fusion is None
    elif retrieval_mode is CitationRetrievalMode.dense_exact:
        valid_shape = lexical is None and dense is not None and fusion is None
    else:
        valid_shape = lexical is not None and dense is not None and fusion is not None
    if not valid_shape:
        raise ValueError("retrieval trace components do not match retrieval mode")
    final_ids = tuple(hit.chunk_id for hit in citations.hits)
    if rerank is not None:
        preceding_ids = {item.chunk_id for item in rerank.candidates}
    elif selection is not None:
        preceding_ids = {item.chunk_id for item in selection.candidates}
    elif fusion is not None:
        preceding_ids = {item.chunk_id for item in fusion.hits}
    elif dense is not None:
        preceding_ids = {item.chunk_id for item in dense.candidates}
    else:
        assert lexical is not None
        preceding_ids = {item.chunk_id for item in lexical.candidates}
    if not set(final_ids).issubset(preceding_ids):
        raise ValueError("retrieval trace final hits were not produced by prior stages")

    candidates: dict[str, object] = {}
    decisions: dict[str, object] = {}
    if lexical is not None:
        candidates["lexical"] = asdict(lexical)
        decisions["lexical"] = [asdict(item) for item in lexical.decisions]
    if dense is not None:
        candidates[dense.mode.value] = asdict(dense)
        decisions["dense_vex"] = asdict(dense.decision)
    if selection is not None:
        decisions["selection"] = [asdict(item) for item in selection.decisions]
    if rerank is not None:
        decisions["rerank"] = {
            "failure_kind": rerank.failure_kind,
            "outcome": rerank.outcome,
            "policy_sha256": rerank.policy_sha256,
        }
    return RetrievalTraceArtifact(
        request=request,
        generation_id=generation_id,
        model_lock_artifact_id=model_lock_artifact_id,
        retrieval_mode=retrieval_mode,
        filters=filters,
        candidates=candidates,
        fusion={} if fusion is None else asdict(fusion),
        selection={} if selection is None else asdict(selection),
        rerank={} if rerank is None else asdict(rerank),
        final_hits=tuple(asdict(hit) for hit in citations.hits),
        timings_ms=timings_ms,
        policy_decisions=decisions,
    )


class RetrievalTraceStore:
    """Persistent immutable store for canonical retrieval traces."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, artifact: RetrievalTraceArtifact) -> StoredRetrievalTrace:
        """Publish one trace atomically without overwriting its content address."""

        raw = (_canonical_json(artifact.record()) + "\n").encode("utf-8")
        destination = self._path(artifact.artifact_id)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            if destination.read_bytes() != raw:
                raise ValueError(
                    "retrieval trace content address is occupied by different bytes"
                )
            return self.load(artifact.artifact_id)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{destination.name}.",
            suffix=".writing",
            dir=destination.parent,
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.link(temporary, destination)
            except FileExistsError:
                if destination.read_bytes() != raw:
                    raise ValueError(
                        "retrieval trace content address raced with different bytes"
                    ) from None
            directory = os.open(destination.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            temporary.unlink(missing_ok=True)
        return self.load(artifact.artifact_id)

    def load(self, artifact_id: str) -> StoredRetrievalTrace:
        """Load and verify canonical bytes, identity, and all component hashes."""

        raw = self._path(artifact_id).read_bytes()
        try:
            record = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("retrieval trace is unreadable") from error
        if not isinstance(record, dict):
            raise ValueError("retrieval trace record must be a JSON object")
        if raw != (_canonical_json(record) + "\n").encode("utf-8"):
            raise ValueError("retrieval trace is not canonical JSON")
        payload = dict(record)
        stored_id = payload.pop("artifact_id", None)
        if stored_id != artifact_id or f"sha256:{_sha256_json(payload)}" != artifact_id:
            raise ValueError("retrieval trace content address does not match payload")
        inputs = {
            "filters": record.get("filters"),
            "generation_id": record.get("generation_id"),
            "model_lock_artifact_id": record.get("model_lock_artifact_id"),
            "request": record.get("request"),
            "retrieval_mode": record.get("retrieval_mode"),
        }
        if record.get("execution_id") != f"sha256:{_sha256_json(inputs)}":
            raise ValueError("retrieval trace execution identity is invalid")
        components = {
            name: record.get(name)
            for name in (
                "request",
                "filters",
                "candidates",
                "fusion",
                "selection",
                "rerank",
                "final_hits",
                "timings_ms",
                "policy_decisions",
            )
        }
        expected_hashes = {
            name: _sha256_json(value) for name, value in components.items()
        }
        if record.get("component_hashes") != expected_hashes:
            raise ValueError("retrieval trace component hash mismatch")
        return StoredRetrievalTrace(
            artifact_id=artifact_id,
            content_sha256=hashlib.sha256(raw).hexdigest(),
            byte_length=len(raw),
            record=record,
        )

    def inspect(self, artifact_id: str) -> RetrievalTraceInspection:
        """Return a verified content-safe summary after restart."""

        stored = self.load(artifact_id)
        record = stored.record
        hashes = record.get("component_hashes")
        hits = record.get("final_hits")
        if not isinstance(hashes, Mapping) or not isinstance(hits, Sequence):
            raise ValueError("retrieval trace inspection fields are invalid")
        return RetrievalTraceInspection(
            artifact_id=artifact_id,
            execution_id=str(record.get("execution_id", "")),
            generation_id=str(record.get("generation_id", "")),
            model_lock_artifact_id=str(record.get("model_lock_artifact_id", "")),
            retrieval_mode=str(record.get("retrieval_mode", "")),
            final_hit_count=len(hits),
            component_hashes=MappingProxyType(
                {str(key): str(value) for key, value in hashes.items()}
            ),
        )

    def _path(self, artifact_id: str) -> Path:
        match = _ARTIFACT_ID.fullmatch(artifact_id)
        if match is None:
            raise ValueError("retrieval trace artifact ID must be content-addressed")
        digest = match.group(1)
        return self.root / "objects" / "sha256" / digest[:2] / f"{digest}.json"


def _mapping(record: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = record.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"retrieval trace {key} must be a JSON object")
    return cast(Mapping[str, object], value)


_VOLATILE_REPLAY_FIELDS = frozenset(
    {
        "artifact_id",
        "execution_artifact_id",
        "latency_ms",
        "provider_request_id",
    }
)


def _semantic_projection(value: object) -> object:
    if isinstance(value, Mapping):
        return {
            str(key): _semantic_projection(item)
            for key, item in value.items()
            if key not in _VOLATILE_REPLAY_FIELDS
        }
    if isinstance(value, list | tuple):
        return [_semantic_projection(item) for item in value]
    return value


def compare_retrieval_traces(
    original: StoredRetrievalTrace,
    replay: StoredRetrievalTrace,
) -> RetrievalTraceReplayComparison:
    """Compare verified trace inputs and semantic components, ignoring timings."""

    drifts = []
    input_fields = (
        ("request", RetrievalTraceDriftKind.request),
        ("generation_id", RetrievalTraceDriftKind.generation),
        ("model_lock_artifact_id", RetrievalTraceDriftKind.model),
        ("retrieval_mode", RetrievalTraceDriftKind.retrieval_mode),
        ("filters", RetrievalTraceDriftKind.filters),
    )
    for name, kind in input_fields:
        if original.record.get(name) != replay.record.get(name):
            drifts.append(kind)
    semantic_components = (
        "candidates",
        "fusion",
        "selection",
        "rerank",
        "final_hits",
        "policy_decisions",
    )
    changed = tuple(
        name
        for name in semantic_components
        if _semantic_projection(original.record.get(name))
        != _semantic_projection(replay.record.get(name))
    )
    if drifts:
        outcome = RetrievalTraceReplayOutcome.refused
    elif changed:
        outcome = RetrievalTraceReplayOutcome.diverged
    else:
        outcome = RetrievalTraceReplayOutcome.exact_match
    return RetrievalTraceReplayComparison(
        schema_version="bijux.canon.retrieval.trace_replay.v1",
        original_artifact_id=original.artifact_id,
        replay_artifact_id=replay.artifact_id,
        original_execution_id=str(original.record.get("execution_id", "")),
        replay_execution_id=str(replay.record.get("execution_id", "")),
        outcome=outcome,
        drifts=tuple(drifts),
        changed_components=changed,
    )


def replay_retrieval_trace(
    store: RetrievalTraceStore,
    artifact_id: str,
    executor: RetrievalTraceReplayExecutor,
) -> RetrievalTraceReplayComparison:
    """Recover immutable inputs, execute once, persist, and compare the replay."""

    original = store.load(artifact_id)
    mode_value = original.record.get("retrieval_mode")
    try:
        mode = CitationRetrievalMode(str(mode_value))
    except ValueError as error:
        raise ValueError("retrieval trace mode is invalid") from error
    replay_input = RetrievalTraceReplayInput(
        request=cast(
            Mapping[str, object], _freeze(_mapping(original.record, "request"))
        ),
        generation_id=str(original.record.get("generation_id", "")),
        model_lock_artifact_id=str(original.record.get("model_lock_artifact_id", "")),
        retrieval_mode=mode,
        filters=cast(
            Mapping[str, object], _freeze(_mapping(original.record, "filters"))
        ),
    )
    replay = store.put(executor(replay_input))
    return compare_retrieval_traces(original, replay)


__all__ = [
    "RetrievalTraceArtifact",
    "RetrievalTraceDriftKind",
    "RetrievalTraceInspection",
    "RetrievalTraceReplayComparison",
    "RetrievalTraceReplayExecutor",
    "RetrievalTraceReplayInput",
    "RetrievalTraceReplayOutcome",
    "RetrievalTraceStore",
    "StoredRetrievalTrace",
    "build_retrieval_trace",
    "compare_retrieval_traces",
    "replay_retrieval_trace",
]
