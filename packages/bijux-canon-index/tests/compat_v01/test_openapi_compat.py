# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi <bijan@bijux.io>
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return cast(dict[str, Any], payload)


def test_openapi_v01_compatibility() -> None:
    fixtures = Path(__file__).resolve().parents[1] / "fixtures"
    v01 = _load(fixtures / "openapi_v0_1.json")
    package_root = Path(__file__).resolve().parents[2]
    repo_root = package_root.parents[1]
    v02 = _load(repo_root / "apis/bijux-canon-index/v1/pinned_openapi.json")

    v01_paths = v01.get("paths", {})
    v02_paths = v02.get("paths", {})
    for path, methods in v01_paths.items():
        assert path in v02_paths
        for method in methods:
            assert method in v02_paths[path]

    v01_components = v01.get("components", {}).get("schemas", {})
    v02_components = v02.get("components", {}).get("schemas", {})
    for name, schema in v01_components.items():
        if name not in v02_components:
            continue
        required = set(schema.get("required", []))
        current_required = set(v02_components[name].get("required", []))
        assert required.issubset(current_required)
