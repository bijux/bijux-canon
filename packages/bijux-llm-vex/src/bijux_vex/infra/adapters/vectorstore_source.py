# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from collections.abc import Iterable
import json
from typing import Any

from bijux_vex.contracts.resources import VectorSource
from bijux_vex.core.determinism import classify_execution
from bijux_vex.core.errors import BackendCapabilityError, ValidationError
from bijux_vex.core.types import Chunk, Document, ExecutionRequest, Result, Vector
from bijux_vex.domain.execution_requests import scoring
from bijux_vex.infra.adapters.vectorstore_metadata import build_vectorstore_metadata
from bijux_vex.infra.adapters.vectorstore_registry import VectorStoreResolution
from bijux_vex.infra.logging import log_event


class VectorStoreVectorSource(VectorSource):
    def __init__(self, base: VectorSource, resolved: VectorStoreResolution):
        self._base = base
        self._resolved = resolved
        self._adapter = resolved.adapter

    @property
    def vector_store_metadata(self) -> dict[str, object]:
        index_params = getattr(self._adapter, "index_params", None)
        return {
            "backend": self._resolved.descriptor.name,
            "uri_redacted": self._resolved.uri_redacted,
            "index_params": index_params,
            "supports_exact": self._resolved.descriptor.supports_exact,
            "supports_ann": self._resolved.descriptor.supports_ann,
            "delete_supported": self._resolved.descriptor.delete_supported,
            "filtering_supported": self._resolved.descriptor.filtering_supported,
            "deterministic_exact": self._resolved.descriptor.deterministic_exact,
            "experimental": self._resolved.descriptor.experimental,
            "consistency": self._resolved.descriptor.consistency,
        }

    # Document operations
    def put_document(self, tx: Any, document: Document) -> None:
        self._base.put_document(tx, document)

    def get_document(self, document_id: str) -> Document | None:
        return self._base.get_document(document_id)

    def list_documents(self) -> Iterable[Document]:
        return self._base.list_documents()

    def delete_document(self, tx: Any, document_id: str) -> None:
        self._base.delete_document(tx, document_id)

    # Chunk operations
    def put_chunk(self, tx: Any, chunk: Chunk) -> None:
        self._base.put_chunk(tx, chunk)

    def get_chunk(self, chunk_id: str) -> Chunk | None:
        return self._base.get_chunk(chunk_id)

    def list_chunks(self, document_id: str | None = None) -> Iterable[Chunk]:
        return self._base.list_chunks(document_id=document_id)

    def delete_chunk(self, tx: Any, chunk_id: str) -> None:
        self._base.delete_chunk(tx, chunk_id)

    # Vector operations
    def put_vector(self, tx: Any, vector: Vector) -> None:
        self._base.put_vector(tx, vector)
        if getattr(self._adapter, "is_noop", False):
            return
        chunk = self._base.get_chunk(vector.chunk_id)
        document_id = chunk.document_id if chunk else ""
        metadata = build_vectorstore_metadata(
            vector=vector,
            document_id=document_id,
            source_uri=None,
            tags=None,
        )
        metadata["vector_id"] = vector.vector_id
        self._adapter.insert([list(vector.values)], metadata=[metadata])

    def get_vector(self, vector_id: str) -> Vector | None:
        return self._base.get_vector(vector_id)

    def list_vectors(self, chunk_id: str | None = None) -> Iterable[Vector]:
        return self._base.list_vectors(chunk_id=chunk_id)

    def query(self, artifact_id: str, request: ExecutionRequest) -> Iterable[Result]:
        if request.vector is None:
            raise ValidationError(message="execution vector required")
        if getattr(self._adapter, "is_noop", False):
            return self._base.query(artifact_id, request)
        options = getattr(self._adapter, "options", None)
        if options is None:
            options = getattr(self._adapter, "_options", None)
        filter_spec: dict[str, Any] | None = None
        if isinstance(options, dict) and "filter" in options:
            raw_filter = options["filter"]
            if isinstance(raw_filter, str):
                try:
                    filter_spec = json.loads(raw_filter)
                except json.JSONDecodeError as exc:
                    raise ValidationError(
                        message="Invalid filter JSON payload"
                    ) from exc
            elif isinstance(raw_filter, dict):
                filter_spec = dict(raw_filter)
            else:
                raise ValidationError(message="Unsupported filter payload type")
        classify_execution(
            contract=request.execution_contract,
            randomness=None,
            ann_runner=None,
            vector_store=self._resolved.descriptor,
            require_randomness=False,
        )
        results: list[Result] = []
        for vector_id, score in self._adapter.query(
            list(request.vector), request.top_k, mode=request.execution_contract.value
        ):
            vec = self._base.get_vector(vector_id)
            if vec is None:
                continue
            chunk = self._base.get_chunk(vec.chunk_id)
            document_id = chunk.document_id if chunk else ""
            results.append(
                Result(
                    request_id=request.request_id,
                    document_id=document_id,
                    chunk_id=vec.chunk_id,
                    vector_id=vector_id,
                    artifact_id=artifact_id,
                    score=float(score),
                    rank=0,
                )
            )
        if filter_spec and not self._resolved.descriptor.filtering_supported:
            supported_keys = {"doc_id", "chunk_id", "source_uri", "tags"}
            unknown = set(filter_spec) - supported_keys
            if unknown:
                raise BackendCapabilityError(
                    message="Vector store filtering requested but backend does not support filters"
                )
            log_event(
                "filter_postprocess",
                backend=self._resolved.descriptor.name,
                warning="post-filter applied in-memory; performance may degrade",
            )
            filtered: list[Result] = []
            for res in results:
                if not self._matches_filter(res, filter_spec):
                    continue
                filtered.append(res)
            results = filtered
        results.sort(key=scoring.tie_break_key)
        limited = results[: request.top_k]
        for idx, res in enumerate(limited, start=1):
            limited[idx - 1] = Result(
                request_id=res.request_id,
                document_id=res.document_id,
                chunk_id=res.chunk_id,
                vector_id=res.vector_id,
                artifact_id=res.artifact_id,
                score=res.score,
                rank=idx,
            )
        return limited

    def delete_vector(self, tx: Any, vector_id: str) -> None:
        self._base.delete_vector(tx, vector_id)
        if getattr(self._adapter, "is_noop", False):
            return
        if not self._resolved.descriptor.delete_supported:
            raise BackendCapabilityError(
                message="Vector store backend does not support deletes"
            )
        self._adapter.delete([vector_id])

    def _matches_filter(self, result: Result, filter_spec: dict[str, Any]) -> bool:
        doc_id = result.document_id
        chunk_id = result.chunk_id
        document = self._base.get_document(doc_id) if doc_id else None
        source_uri = document.source if document else None
        tags = filter_spec.get("tags")
        if "doc_id" in filter_spec:
            expected = filter_spec["doc_id"]
            if isinstance(expected, (list, tuple, set)):
                if doc_id not in expected:
                    return False
            elif doc_id != expected:
                return False
        if "chunk_id" in filter_spec:
            expected = filter_spec["chunk_id"]
            if isinstance(expected, (list, tuple, set)):
                if chunk_id not in expected:
                    return False
            elif chunk_id != expected:
                return False
        if "source_uri" in filter_spec:
            expected = filter_spec["source_uri"]
            if source_uri != expected:
                return False
        if tags is not None:
            if not isinstance(tags, (list, tuple, set)):
                tags = [tags]
            vector = self._base.get_vector(result.vector_id)
            vector_tags = set()
            if vector and vector.metadata:
                meta_dict = dict(vector.metadata)
                vector_tags = set(meta_dict.get("tags", ()))
            if not set(tags).issubset(vector_tags):
                return False
        return True


__all__ = ["VectorStoreVectorSource"]
