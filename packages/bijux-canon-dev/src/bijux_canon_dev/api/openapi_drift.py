from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
from typing import Any

import yaml


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare a checked-in OpenAPI schema against a live ASGI app.",
    )
    parser.add_argument(
        "--app-import",
        required=True,
        help="Import path in module:attribute form. The attribute may be an app or a factory.",
    )
    parser.add_argument(
        "--schema",
        required=True,
        help="Path to the checked-in schema file (.json, .yaml, or .yml).",
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Path to write the generated OpenAPI payload as canonical JSON.",
    )
    parser.add_argument(
        "--pin",
        action="store_true",
        help="Write the generated schema back to --schema instead of failing on drift.",
    )
    return parser.parse_args()


def load_target(entrypoint: str) -> Any:
    module_name, separator, attribute_name = entrypoint.partition(":")
    if not separator or not module_name or not attribute_name:
        raise SystemExit(
            f"Invalid --app-import value '{entrypoint}'. Use module:attribute."
        )
    module = importlib.import_module(module_name)
    target = getattr(module, attribute_name)
    return target() if callable(target) else target


def load_schema(path: Path) -> Any:
    if not path.exists():
        raise SystemExit(f"Schema file not found: {path}")
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        return yaml.safe_load(text)
    return json.loads(text)


def write_schema(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() in {".yaml", ".yml"}:
        path.write_text(
            yaml.safe_dump(payload, sort_keys=False, allow_unicode=False),
            encoding="utf-8",
        )
        return
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_generated_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def canonicalize(payload: Any) -> Any:
    return json.loads(json.dumps(payload, sort_keys=True))


def main() -> int:
    args = parse_args()
    app = load_target(args.app_import)
    generated = canonicalize(app.openapi())

    schema_path = Path(args.schema)
    output_path = Path(args.out)
    write_generated_json(output_path, generated)

    if args.pin:
        write_schema(schema_path, generated)
        print(f"Pinned OpenAPI schema to {schema_path}")
        return 0

    expected = canonicalize(load_schema(schema_path))
    if generated != expected:
        raise SystemExit(
            "OpenAPI drift detected.\n"
            f"- Generated: {output_path}\n"
            f"- Expected:  {schema_path}\n"
            "If the change is intentional, rerun with --pin and commit the schema update."
        )

    print(f"OpenAPI matches checked-in schema: {schema_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
