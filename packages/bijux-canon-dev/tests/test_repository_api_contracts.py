from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

import yaml


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bijux_canon_dev.api.openapi_drift import canonicalize


REPO_ROOT = Path(__file__).resolve().parents[3]
CONTRACT_ARTIFACTS = {
    "apis/bijux-canon-agent/v1/schema.yaml": "bijux-canon-agent API",
    "apis/bijux-canon-index/v1/schema.yaml": "bijux-canon-index API",
    "apis/bijux-canon-index/v1/openapi.v1.json": "bijux-canon-index API",
    "apis/bijux-canon-ingest/v1/schema.yaml": "bijux-canon-ingest API",
    "apis/bijux-canon-reason/v1/schema.yaml": "bijux-canon-reason API",
    "apis/bijux-canon-reason/v1/pinned_openapi.json": "bijux-canon-reason API",
    "apis/bijux-canon-runtime/v1/schema.yaml": "bijux-canon-runtime API",
}
ARTIFACT_PAIRS = [
    (
        "apis/bijux-canon-index/v1/schema.yaml",
        "apis/bijux-canon-index/v1/openapi.v1.json",
    ),
    (
        "apis/bijux-canon-reason/v1/schema.yaml",
        "apis/bijux-canon-reason/v1/pinned_openapi.json",
    ),
]
LEGACY_MARKERS = (
    "bijux-rag",
    "bijux-rar",
    "placeholder",
    "llm rar",
)


def _load_artifact(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        return json.loads(text)
    return yaml.safe_load(text)


def test_repository_api_contracts_share_a_common_baseline() -> None:
    for relative_path, expected_title in CONTRACT_ARTIFACTS.items():
        path = REPO_ROOT / relative_path
        payload = _load_artifact(path)
        info = payload["info"]

        assert payload["openapi"] == "3.1.0"
        assert info["title"] == expected_title
        assert info["version"] == "v1"
        assert info["license"]["name"] == "Apache 2.0"
        assert info["contact"]["name"] == "Bijux"
        assert payload["servers"] == [{"url": "/"}]
        assert payload["paths"], f"{relative_path} must expose at least one path"


def test_repository_api_contract_pairs_stay_in_sync() -> None:
    for left_relative, right_relative in ARTIFACT_PAIRS:
        left = _load_artifact(REPO_ROOT / left_relative)
        right = _load_artifact(REPO_ROOT / right_relative)
        assert canonicalize(left) == canonicalize(right)


def test_repository_api_contracts_do_not_carry_legacy_labels() -> None:
    for relative_path in CONTRACT_ARTIFACTS:
        text = (REPO_ROOT / relative_path).read_text(encoding="utf-8").lower()
        for marker in LEGACY_MARKERS:
            assert marker not in text, f"{relative_path} still contains legacy marker {marker!r}"
