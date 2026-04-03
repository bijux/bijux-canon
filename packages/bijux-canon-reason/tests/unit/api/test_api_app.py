# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from bijux_canon_reason.api.v1.app import create_app


def test_api_app_creates_fastapi_instance() -> None:
    app = create_app()
    assert app.title
    # ensure routes exist (health and runs)
    paths = {route.path for route in app.router.routes}
    assert any("/health" in p for p in paths)
