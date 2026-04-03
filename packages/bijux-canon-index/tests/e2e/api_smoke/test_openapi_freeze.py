# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations
from fastapi.encoders import jsonable_encoder

from bijux_canon_index.api.v1.app import build_app
from bijux_canon_index.core.canon import canon
from bijux_canon_index.core.identity.ids import fingerprint

EXPECTED_OPENAPI_FINGERPRINT = (
    "892b5bbe59443c641e778c4998b67ec949dc6b20eee8bbde8bb6c8008f83e4b9"
)


def test_openapi_schema_is_frozen():
    app = build_app()
    schema = jsonable_encoder(app.openapi())
    fp = fingerprint(canon(schema))
    assert fp == EXPECTED_OPENAPI_FINGERPRINT
