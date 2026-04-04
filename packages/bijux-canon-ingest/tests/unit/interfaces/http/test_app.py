# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from fastapi.testclient import TestClient

from bijux_canon_ingest.interfaces.http.app import create_app


def _docs() -> list[dict[str, str]]:
    return [
        {
            "doc_id": "d1",
            "text": "Mitochondria are the powerhouse of the cell.",
            "title": "Mito",
            "category": "bio",
        },
        {
            "doc_id": "d2",
            "text": "Chloroplasts perform photosynthesis in plants.",
            "title": "Chloro",
            "category": "bio",
        },
    ]


def test_openapi_reports_package_title() -> None:
    client = TestClient(create_app())

    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "bijux-canon-ingest"


def test_ask_endpoint_returns_grounded_payload_shape() -> None:
    client = TestClient(create_app())

    build_response = client.post(
        "/v1/index/build",
        json={
            "docs": _docs(),
            "backend": "bm25",
            "chunk_size": 64,
            "overlap": 0,
        },
    )
    assert build_response.status_code == 200
    index_id = build_response.json()["index_id"]

    ask_response = client.post(
        "/v1/ask",
        json={
            "index_id": index_id,
            "query": "What is the powerhouse of the cell?",
            "top_k": 3,
            "rerank": True,
            "filters": {},
        },
    )

    assert ask_response.status_code == 200
    payload = ask_response.json()
    assert payload["answer"]
    assert payload["citations"][0]["doc_id"] == "d1"
    assert payload["candidates"][0]["chunk"]["doc_id"] == "d1"


def test_ask_endpoint_reports_unknown_index() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/v1/ask",
        json={
            "index_id": "missing",
            "query": "anything",
            "top_k": 1,
            "rerank": True,
            "filters": {},
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Unknown index_id"
