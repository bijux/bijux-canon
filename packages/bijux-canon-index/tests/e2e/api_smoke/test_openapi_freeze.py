# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from bijux_canon_index.api.v1.app import build_app
from bijux_canon_index.core.canon import canon
from bijux_canon_index.core.identity.ids import fingerprint
from fastapi.encoders import jsonable_encoder

EXPECTED_OPENAPI_FINGERPRINT = (
    "86e05d449595b8aacab8273c170b8d716b9f3bec4232072228acae05bba7ebcb"
)


def test_openapi_schema_is_frozen():
    app = build_app()
    schema = jsonable_encoder(app.openapi())
    fp = fingerprint(canon(schema))
    assert fp == EXPECTED_OPENAPI_FINGERPRINT
