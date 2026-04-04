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


def build_openapi_factory(app: FastAPI) -> Any:
    """Create the custom OpenAPI callback for the FastAPI app."""

    def _custom_openapi() -> dict[str, Any]:
        existing_schema = app.openapi_schema
        if isinstance(existing_schema, dict):
            return existing_schema
        app.openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            routes=app.routes,
            openapi_version="3.1.0",
            summary=app.summary,
            description=app.description,
            tags=app.openapi_tags,
            servers=app.servers,
            contact=app.contact,
            license_info=app.license_info,
        )
        generated_schema = app.openapi_schema
        if not isinstance(
            generated_schema, dict
        ):  # pragma: no cover - FastAPI contract
            raise RuntimeError("FastAPI returned a non-dict OpenAPI schema")
        return generated_schema

    return _custom_openapi


__all__ = ["InMemoryIndexStore", "build_openapi_factory", "index_backend_from_name"]
