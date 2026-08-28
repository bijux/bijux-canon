from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, cast

REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLE = REPO_ROOT / "examples" / "urban-heat-research"


def _load(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def test_generalization_corpus_has_exact_license_and_provenance_records() -> None:
    manifest = _load(EXAMPLE / "corpus-manifest.json")

    assert manifest["schema_version"] == (
        "bijux.canon.generalization_corpus_manifest.v1"
    )
    assert manifest["source_count"] == len(manifest["sources"]) == 4
    assert manifest["license"]["expression"] == "Apache-2.0"
    assert manifest["provenance"] == {
        "authorship": "Bijux repository authors",
        "created_for": "Deterministic installed-product generalization acceptance",
        "external_source": None,
        "synthetic": True,
        "transformations": [],
    }
    assert {source["format_id"] for source in manifest["sources"]} == {
        "html",
        "jats",
        "markdown",
        "text",
    }
    for source in manifest["sources"]:
        path = EXAMPLE / source["local_path"]
        content = path.read_bytes()
        assert len(content) == source["byte_count"]
        assert hashlib.sha256(content).hexdigest() == source["sha256"]


def test_generalization_acceptance_is_strict_and_predeclared() -> None:
    acceptance = _load(EXAMPLE / "acceptance.json")
    cases = acceptance["cases"]

    assert acceptance["system_output_may_define_truth"] is False
    assert {case["kind"] for case in cases} == {
        "conflict",
        "supported",
        "unsupported",
    }
    assert all(
        case["requirements"]["unsupported_material_claims_max"] == 0 for case in cases
    )
    assert all(
        case["requirements"].get("citation_resolution_ratio_min", 1.0) == 1.0
        for case in cases
    )
    unsupported = next(case for case in cases if case["kind"] == "unsupported")
    assert unsupported["requirements"] == {
        "answer_disposition": "abstained",
        "citation_count_max": 0,
        "material_claims_max": 0,
        "unsupported_material_claims_max": 0,
    }
    assert (
        acceptance["research"]["requirements"]["unsupported_material_claims_max"] == 0
    )


def test_product_source_contains_no_generalization_fixture_rules() -> None:
    product_roots = tuple((REPO_ROOT / "packages").glob("bijux-canon-*/src"))
    fixture_markers = ("eos-9", "reflective roofs", "urban-heat-operations")
    matches: list[str] = []
    for root in product_roots:
        for path in root.rglob("*.py"):
            text = path.read_text(encoding="utf-8").lower()
            for marker in fixture_markers:
                if marker in text:
                    matches.append(f"{path.relative_to(REPO_ROOT)}: {marker}")
    assert not matches, (
        "generalization fixture leaked into product rules:\n" + "\n".join(matches)
    )
