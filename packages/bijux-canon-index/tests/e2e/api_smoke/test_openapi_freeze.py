# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations
from fastapi.encoders import jsonable_encoder

from bijux_canon_index.api.v1.app import build_app
from bijux_canon_index.core.canon import canon
from bijux_canon_index.core.identity.ids import fingerprint

EXPECTED_OPENAPI_FINGERPRINT = (
    "69fe209b0242d4054bac98b6bed870c5e97ebc4a461997a342e57139f82fc9e5"
)


def test_openapi_schema_is_frozen():
    app = build_app()
    schema = jsonable_encoder(app.openapi())
    fp = fingerprint(canon(schema))
    assert fp == EXPECTED_OPENAPI_FINGERPRINT
