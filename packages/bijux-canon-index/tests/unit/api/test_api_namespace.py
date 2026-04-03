# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations
from bijux_vex.api.v1 import build_app


def test_v1_build_app_exposes_fastapi_instance() -> None:
    app = build_app()
    assert app.title.lower().startswith("bijux-canon-index")
    assert app.version == "v1"
