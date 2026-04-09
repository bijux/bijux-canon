# SPDX-License-Identifier: Apache-2.0
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
from pathlib import Path

from openapi_spec_validator import validate


def test_openapi_v1_is_valid() -> None:
    package_root = Path(__file__).resolve().parents[3]
    repo_root = package_root.parents[1]
    schema_path = (
        repo_root / "apis" / "bijux-canon-index" / "v1" / "pinned_openapi.json"
    )
    assert schema_path.exists(), "OpenAPI v1 schema must be generated"
    data = json.loads(schema_path.read_text())
    validate(data)
