from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bijux_canon_dev.api.openapi_drift import canonicalize

REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_CONTRACT_TITLES = {
    "bijux-canon-agent": "bijux-canon-agent API",
    "bijux-canon-index": "bijux-canon-index API",
    "bijux-canon-ingest": "bijux-canon-ingest API",
    "bijux-canon-reason": "bijux-canon-reason API",
    "bijux-canon-runtime": "bijux-canon-runtime API",
}
EXPECTED_ARTIFACTS = ("pinned_openapi.json", "schema.hash", "schema.yaml")
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


def _extract_hash_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        values[key.strip()] = value.strip()
    return values


def test_repository_api_contracts_share_a_common_baseline() -> None:
    for package_name, expected_title in PACKAGE_CONTRACT_TITLES.items():
        package_dir = REPO_ROOT / "apis" / package_name / "v1"
        payload = _load_artifact(package_dir / "schema.yaml")
        info = payload["info"]

        assert payload["openapi"] == "3.1.0"
        assert info["title"] == expected_title
        assert info["version"] == "v1"
        assert info["license"]["name"] == "Apache 2.0"
        assert info["contact"]["name"] == "Bijux"
        assert payload["servers"] == [{"url": "/"}]
        assert payload["paths"], f"{package_name} must expose at least one path"


def test_repository_api_contract_pairs_stay_in_sync() -> None:
    for package_name in PACKAGE_CONTRACT_TITLES:
        package_dir = REPO_ROOT / "apis" / package_name / "v1"
        left = _load_artifact(package_dir / "schema.yaml")
        right = _load_artifact(package_dir / "pinned_openapi.json")
        assert canonicalize(left) == canonicalize(right)


def test_repository_api_contract_trees_are_symmetrical() -> None:
    for package_name in PACKAGE_CONTRACT_TITLES:
        package_dir = REPO_ROOT / "apis" / package_name / "v1"
        assert (
            tuple(sorted(path.name for path in package_dir.iterdir()))
            == EXPECTED_ARTIFACTS
        )


def test_repository_api_schema_hashes_match_yaml_contracts() -> None:
    for package_name in PACKAGE_CONTRACT_TITLES:
        package_dir = REPO_ROOT / "apis" / package_name / "v1"
        schema_text = (package_dir / "schema.yaml").read_text(encoding="utf-8")
        stored = _extract_hash_file(package_dir / "schema.hash")
        assert stored["version"] == "v1"
        assert (
            stored["sha256"] == hashlib.sha256(schema_text.encode("utf-8")).hexdigest()
        )


def test_repository_api_contracts_do_not_carry_legacy_labels() -> None:
    for package_name in PACKAGE_CONTRACT_TITLES:
        for artifact_name in EXPECTED_ARTIFACTS:
            relative_path = f"apis/{package_name}/v1/{artifact_name}"
            text = (REPO_ROOT / relative_path).read_text(encoding="utf-8").lower()
            for marker in LEGACY_MARKERS:
                assert marker not in text, (
                    f"{relative_path} still contains legacy marker {marker!r}"
                )
