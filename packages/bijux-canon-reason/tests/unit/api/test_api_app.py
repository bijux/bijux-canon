# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from bijux_canon_reason.api.v1.app import create_app


def test_api_app_creates_fastapi_instance() -> None:
    app = create_app()
    assert app.title
    # ensure routes exist (health and runs)
    paths = {
        path
        for route in app.router.routes
        if isinstance((path := getattr(route, "path", None)), str)
    }
    assert any("/health" in p for p in paths)


def test_openapi_schema_links_created_resources_to_follow_up_operations() -> None:
    app = create_app()
    schema = app.openapi()
    item_links = schema["paths"]["/v1/items"]["post"]["responses"]["201"]["links"]
    run_links = schema["paths"]["/v1/runs"]["post"]["responses"]["200"]["links"]

    assert item_links["getCreatedItem"]["operationId"] == "getReasonItem"
    assert item_links["getCreatedItem"]["parameters"]["item_id"] == "$response.body#/id"
    assert item_links["updateCreatedItem"]["operationId"] == "updateReasonItem"
    assert item_links["deleteCreatedItem"]["operationId"] == "deleteReasonItem"

    assert run_links["getCreatedRun"]["operationId"] == "getReasonRun"
    assert (
        run_links["getCreatedRun"]["parameters"]["run_id"] == "$response.body#/run_id"
    )
    assert run_links["getCreatedRunManifest"]["operationId"] == "getReasonRunManifest"
    assert run_links["getCreatedRunTrace"]["operationId"] == "getReasonRunTrace"
    assert run_links["verifyCreatedRun"]["operationId"] == "verifyReasonRun"
    assert run_links["replayCreatedRun"]["operationId"] == "replayReasonRun"
