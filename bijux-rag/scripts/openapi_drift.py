# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Check OpenAPI drift between FastAPI app and schema file.")
    parser.add_argument("--schema", required=True, help="Path to checked-in OpenAPI schema (YAML)")
    parser.add_argument("--out", required=True, help="Path to write generated OpenAPI JSON")
    args = parser.parse_args()

    try:
        import fastapi  # type: ignore
        import yaml  # type: ignore
    except Exception as exc:  # pragma: no cover
        print(f"✘ Missing dependencies to generate OpenAPI: {exc}", file=sys.stderr)
        return 1

    from bijux_rag.boundaries.web.fastapi_app import create_app

    app = create_app()
    generated = app.openapi()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(generated, sort_keys=True, indent=2), encoding="utf-8")

    schema_path = Path(args.schema)
    try:
        with schema_path.open("r", encoding="utf-8") as f:
            expected = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"✘ Missing schema file: {schema_path}", file=sys.stderr)
        return 1

    if generated != expected:
        print("✘ OpenAPI drift detected. Regenerate schema.yaml from app.openapi() and commit.", file=sys.stderr)
        return 1

    print("✔ OpenAPI matches checked-in schema")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
