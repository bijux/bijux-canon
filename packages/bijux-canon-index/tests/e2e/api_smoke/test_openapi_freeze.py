# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations
from fastapi.encoders import jsonable_encoder

from bijux_vex.boundaries.api.app import build_app
from bijux_vex.core.canon import canon
from bijux_vex.core.identity.ids import fingerprint

EXPECTED_OPENAPI_FINGERPRINT = (
    "3838a62cbe68daac9125a0974e6634cbfc5d3cb3a9489fca8f76cc7e00658cba"
)


def test_openapi_schema_is_frozen():
    app = build_app()
    schema = jsonable_encoder(app.openapi())
    fp = fingerprint(canon(schema))
    assert fp == EXPECTED_OPENAPI_FINGERPRINT
