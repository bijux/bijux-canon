from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker, ValidationError
from referencing import Registry, Resource


PACKAGE_CONFIG = {
    "agent": {
        "api": "bijux-canon-agent",
        "distribution": "bijux-canon-agent",
        "module": "bijux_canon_agent",
        "schema_sections": ["schema_bundle"],
        "example_sections": ["conformance"],
    },
    "index": {
        "api": "bijux-canon-index",
        "distribution": "bijux-canon-index",
        "module": "bijux_canon_index",
        "schema_sections": ["schema_bundle", "retrieval_schema_bundle"],
        "example_sections": ["conformance_example", "retrieval_conformance_example"],
    },
    "ingest": {
        "api": "bijux-canon-ingest",
        "distribution": "bijux-canon-ingest",
        "module": "bijux_canon_ingest",
        "schema_sections": ["schemas"],
        "example_sections": ["conformance_examples"],
    },
    "reason": {
        "api": "bijux-canon-reason",
        "distribution": "bijux-canon-reason",
        "module": "bijux_canon_reason",
        "schema_sections": ["schema_bundle"],
        "example_sections": ["conformance_example"],
    },
    "runtime": {
        "api": "bijux-canon-runtime",
        "distribution": "bijux-canon-runtime",
        "module": "bijux_canon_runtime",
        "schema_sections": ["schema_bundle"],
        "example_sections": ["conformance"],
    },
}


def canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    assert isinstance(value, dict)
    return value


def json_type(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    raise AssertionError(type(value))


def artifact_identity(record: dict[str, Any]) -> str:
    payload = copy.deepcopy(record)
    payload.pop("artifact_id")
    return "sha256:" + digest(canonical(payload))


def manifest_schema_entries(
    package: str, manifest: dict[str, Any]
) -> list[dict[str, Any]]:
    if package == "ingest":
        return [
            {"artifact_type": artifact_type, **entry}
            for artifact_type, entry in sorted(manifest["schemas"].items())
        ]
    entries = []
    for section in PACKAGE_CONFIG[package]["schema_sections"]:
        bundle = manifest[section]
        entries.append(
            {
                "path": bundle["path"],
                "sha256": bundle["sha256"],
                "definitions": dict(sorted(bundle["definitions"].items())),
            }
        )
    return entries


def manifest_example_entries(
    package: str, manifest: dict[str, Any]
) -> list[dict[str, Any]]:
    if package == "ingest":
        return [dict(entry) for _, entry in sorted(manifest["conformance_examples"].items())]
    return [dict(manifest[section]) for section in PACKAGE_CONFIG[package]["example_sections"]]


def schema_for_artifact(
    package: str,
    artifact_type: str,
    schema_entries: list[dict[str, Any]],
    schemas: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if package == "ingest":
        entry = next(entry for entry in schema_entries if entry["artifact_type"] == artifact_type)
        return schemas[entry["path"]]
    definition_name = artifact_type.rsplit(".", 1)[-1]
    entry = next(
        entry
        for entry in schema_entries
        if artifact_type in entry["definitions"]
        or definition_name in entry["definitions"]
    )
    return schemas[entry["path"]]


def validator_for(
    schema: dict[str, Any], schemas: dict[str, dict[str, Any]]
) -> Draft202012Validator:
    registry = Registry().with_resources(
        (document["$id"], Resource.from_contents(document))
        for document in schemas.values()
        if "$id" in document
    )
    return Draft202012Validator(
        schema, registry=registry, format_checker=FormatChecker()
    )


def rejected(validator: Draft202012Validator, value: dict[str, Any]) -> bool:
    try:
        validator.validate(value)
    except ValidationError:
        return True
    return False


def package_closure(repo: Path, package: str) -> tuple[dict[str, Any], list[str]]:
    config = PACKAGE_CONFIG[package]
    root = repo / "apis" / config["api"] / "v2"
    manifest_path = root / "contract-manifest.json"
    manifest = load_json(manifest_path)
    schema_entries = manifest_schema_entries(package, manifest)
    example_entries = manifest_example_entries(package, manifest)
    schema_paths = {entry["path"] for entry in schema_entries}
    if package == "ingest":
        shared = manifest["shared_schema"]
        schema_paths.add(shared["path"])
    schemas = {path: load_json(root / path) for path in sorted(schema_paths)}

    generated_schemas = []
    definition_count = 0
    if package == "ingest":
        expected_hashes = {
            entry["path"]: entry["sha256"] for entry in schema_entries
        }
        expected_hashes[manifest["shared_schema"]["path"]] = manifest["shared_schema"]["sha256"]
        definition_count = len(schema_entries)
    else:
        expected_hashes = {entry["path"]: entry["sha256"] for entry in schema_entries}
        definition_count = sum(len(entry["definitions"]) for entry in schema_entries)
    for path in sorted(schemas):
        schema_path = root / path
        assert digest(schema_path.read_bytes()) == expected_hashes[path]
        Draft202012Validator.check_schema(schemas[path])
        generated_schemas.append(
            {
                "path": f"apis/{config['api']}/v2/{path}",
                "file_sha256": expected_hashes[path],
                "canonical_sha256": digest(canonical(schemas[path])),
            }
        )

    migration_entry = manifest["migration_policy"]
    migration_path = root / migration_entry["path"]
    assert digest(migration_path.read_bytes()) == migration_entry["sha256"]
    migration = load_json(migration_path)
    rules = migration.get("migration_rules", migration)
    assert rules["implicit_migration_allowed"] is False
    assert migration["registered_transforms"] == []

    fixtures: dict[str, dict[str, Any]] = {}
    record_count = 0
    drift_rejections = 0
    migration_rejections = 0
    artifact_ids: list[str] = []
    example_files = []
    for entry in example_entries:
        example_path = root / entry["path"]
        assert digest(example_path.read_bytes()) == entry["sha256"]
        bundle = load_json(example_path)
        records = bundle["records"]
        assert len(records) == entry["record_count"]
        record_count += len(records)
        example_files.append(
            {
                "path": f"apis/{config['api']}/v2/{entry['path']}",
                "sha256": entry["sha256"],
                "record_count": len(records),
            }
        )
        for record in records:
            artifact_type = record["artifact_type"]
            schema = schema_for_artifact(package, artifact_type, schema_entries, schemas)
            validator = validator_for(schema, schemas)
            validator.validate(record)
            assert artifact_identity(record) == record["artifact_id"]
            artifact_ids.append(record["artifact_id"])
            fixtures.setdefault(
                artifact_type,
                {
                    "artifact_id": record["artifact_id"],
                    "field_types": {
                        key: json_type(value) for key, value in sorted(record.items())
                    },
                    "required_fields": sorted(record),
                },
            )
            drifted = copy.deepcopy(record)
            drifted["unregistered_field"] = True
            assert rejected(validator, drifted)
            drift_rejections += 1
            for version in ("1.0.0", "3.0.0"):
                migrated = copy.deepcopy(record)
                migrated["schema_version"] = version
                assert rejected(validator, migrated)
                migration_rejections += 1

    assert len(fixtures) == definition_count
    package_result = {
        "artifact_schema_version": manifest["artifact_schema_version"],
        "contract_id": manifest["contract_id"],
        "manifest_path": f"apis/{config['api']}/v2/contract-manifest.json",
        "manifest_sha256": digest(manifest_path.read_bytes()),
        "schema_document_count": len(generated_schemas),
        "artifact_definition_count": definition_count,
        "example_file_count": len(example_files),
        "record_count": record_count,
        "generated_schemas": generated_schemas,
        "example_files": example_files,
        "typed_compatibility_fixtures": dict(sorted(fixtures.items())),
        "drift_rejection_count": drift_rejections,
        "migration_boundaries": {
            "v1_to_v2": "rejected_unregistered_transform",
            "v2_to_v1": "rejected_unregistered_transform",
            "rejection_count": migration_rejections,
        },
    }
    return package_result, artifact_ids


def generate_closure(repo: Path) -> dict[str, Any]:
    packages = {}
    artifact_ids: list[str] = []
    for package in sorted(PACKAGE_CONFIG):
        packages[package], ids = package_closure(repo, package)
        artifact_ids.extend(ids)
    assert len(artifact_ids) == len(set(artifact_ids))
    schema_documents = sum(
        package["schema_document_count"] for package in packages.values()
    )
    definitions = sum(
        package["artifact_definition_count"] for package in packages.values()
    )
    records = sum(package["record_count"] for package in packages.values())
    drift_rejections = sum(
        package["drift_rejection_count"] for package in packages.values()
    )
    migration_rejections = sum(
        package["migration_boundaries"]["rejection_count"]
        for package in packages.values()
    )
    source_payload = {
        name: {
            "manifest_sha256": package["manifest_sha256"],
            "generated_schemas": package["generated_schemas"],
            "example_files": package["example_files"],
        }
        for name, package in packages.items()
    }
    return {
        "schema_version": "bijux.canon.schema_closure.v1",
        "status": "verified",
        "source_tree_sha256": digest(canonical(source_payload)),
        "package_boundary_count": len(packages),
        "schema_document_count": schema_documents,
        "artifact_definition_count": definitions,
        "example_record_count": records,
        "drift_rejection_count": drift_rejections,
        "migration_rejection_count": migration_rejections,
        "identity_collision_count": 0,
        "packages": packages,
    }


def installed_surfaces() -> dict[str, dict[str, str]]:
    results = {}
    for package, config in sorted(PACKAGE_CONFIG.items()):
        distribution = importlib.metadata.distribution(config["distribution"])
        origin = Path(
            distribution.locate_file(
                Path(config["module"]) / "__init__.py"
            )
        ).resolve()
        assert origin.is_file()
        assert "site-packages" in origin.parts
        assert "/packages/" not in str(origin)
        results[package] = {
            "distribution": config["distribution"],
            "version": distribution.version,
            "import_origin": str(origin),
        }
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-installed", action="store_true")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[3]
    closure = generate_closure(repo)
    if args.write:
        args.output.write_text(json.dumps(closure, indent=2, sort_keys=True) + "\n")
    else:
        assert load_json(args.output) == closure
    installed = installed_surfaces() if args.require_installed else {}
    print(json.dumps({
        "status": "verified",
        "mode": "write" if args.write else "check",
        "closure_sha256": digest(canonical(closure)),
        "package_boundaries": closure["package_boundary_count"],
        "schema_documents": closure["schema_document_count"],
        "artifact_definitions": closure["artifact_definition_count"],
        "example_records": closure["example_record_count"],
        "drift_rejections": closure["drift_rejection_count"],
        "migration_rejections": closure["migration_rejection_count"],
        "installed_surfaces": installed,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
