# SPDX-License-Identifier: MIT
# SPDX-License-Identifier: MIT
from __future__ import annotations
import json
from pathlib import Path

from openapi_spec_validator import validate


def test_openapi_v1_is_valid() -> None:
    package_root = Path(__file__).resolve().parents[3]
    repo_root = package_root.parents[1]
    schema_path = repo_root / "apis" / "bijux-vex" / "v1" / "openapi.v1.json"
    assert schema_path.exists(), "OpenAPI v1 schema must be generated"
    data = json.loads(schema_path.read_text())
    validate(data)
