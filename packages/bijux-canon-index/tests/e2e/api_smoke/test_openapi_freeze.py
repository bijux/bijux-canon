# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from fastapi.encoders import jsonable_encoder

from bijux_canon_index.api.v1.app import build_app
from bijux_canon_index.core.canon import canon
from bijux_canon_index.core.identity.ids import fingerprint

EXPECTED_OPENAPI_FINGERPRINT = (
    "665625e834ff73a378b1444dd3535e67eca8d4a8e01ade36e7d2d4b3815a6708"
)


def test_openapi_schema_is_frozen() -> None:
    app = build_app()
    schema = jsonable_encoder(app.openapi())
    fp = fingerprint(canon(schema))
    assert fp == EXPECTED_OPENAPI_FINGERPRINT


def test_validation_response_description_is_application_owned() -> None:
    schema = jsonable_encoder(build_app().openapi())

    validation_response = schema["paths"]["/execute"]["post"]["responses"]["422"]

    assert validation_response["description"] == "Unprocessable Entity"
