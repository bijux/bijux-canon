# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from bijux_rar.httpapi import create_app


def test_httpapi_app_creates_fastapi_instance() -> None:
    app = create_app()
    assert app.title
    # ensure routes exist (health and runs)
    paths = {route.path for route in app.router.routes}
    assert any("/health" in p for p in paths)
