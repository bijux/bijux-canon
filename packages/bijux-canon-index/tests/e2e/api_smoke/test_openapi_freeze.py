# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations
from fastapi.encoders import jsonable_encoder

from bijux_canon_index.api.v1.app import build_app
from bijux_canon_index.core.canon import canon
from bijux_canon_index.core.identity.ids import fingerprint

EXPECTED_OPENAPI_FINGERPRINT = (
    "a0f3b8f09954afbc9cf62c64b927af1fefa5e09f15d25fa3514828afff09d59a"
)


def test_openapi_schema_is_frozen():
    app = build_app()
    schema = jsonable_encoder(app.openapi())
    fp = fingerprint(canon(schema))
    assert fp == EXPECTED_OPENAPI_FINGERPRINT
