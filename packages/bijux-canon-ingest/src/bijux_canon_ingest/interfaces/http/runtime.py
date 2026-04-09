# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Boundary runtime helpers for the HTTP adapter."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from bijux_canon_ingest.application.service import IndexBackend, StoredIndex


class InMemoryIndexStore:
    """Process-local index store for the HTTP adapter."""

    def __init__(self) -> None:
        self._indexes: dict[str, StoredIndex] = {}

    def put(self, index: StoredIndex) -> str:
        index_id = f"idx_{index.fingerprint}"
        self._indexes[index_id] = index
        return index_id

    def get(self, index_id: str) -> StoredIndex | None:
        return self._indexes.get(index_id)


def index_backend_from_name(name: str) -> IndexBackend:
    """Map the request backend string to the service enum."""

    if name == "bm25":
        return IndexBackend.BM25
    return IndexBackend.NUMPY_COSINE


class IngestHttpApplication(FastAPI):
    """FastAPI application that serves the repository OpenAPI contract."""

    def openapi(self) -> dict[str, Any]:
        """Build and cache the OpenAPI schema with the repository contract."""

        existing_schema = self.openapi_schema
        if isinstance(existing_schema, dict):
            return existing_schema

        self.openapi_schema = get_openapi(
            title=self.title,
            version=self.version,
            routes=self.routes,
            openapi_version="3.1.0",
            summary=self.summary,
            description=self.description,
            tags=self.openapi_tags,
            servers=self.servers,
            contact=self.contact,
            license_info=self.license_info,
        )
        generated_schema = self.openapi_schema
        if not isinstance(
            generated_schema, dict
        ):  # pragma: no cover - FastAPI contract
            raise RuntimeError("FastAPI returned a non-dict OpenAPI schema")
        return generated_schema


__all__ = ["InMemoryIndexStore", "IngestHttpApplication", "index_backend_from_name"]
