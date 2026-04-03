# SPDX-License-Identifier: MIT
# SPDX-License-Identifier: MIT
from __future__ import annotations
import json
from pathlib import Path

from openapi_spec_validator import validate


def test_openapi_v1_is_valid() -> None:
    schema_path = Path(__file__).parents[3] / "api" / "v1" / "openapi.v1.json"
    assert schema_path.exists(), "OpenAPI v1 schema must be generated"
    data = json.loads(schema_path.read_text())
    validate(data)
