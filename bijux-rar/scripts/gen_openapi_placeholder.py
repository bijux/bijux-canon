# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

import argparse
import json
from pathlib import Path


def generate() -> dict:
    # Deterministic placeholder OpenAPI schema.
    # This exists ONLY to prove the drift-check mechanism works until the real API ships.
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "bijux-rar API (placeholder)",
            "version": "0.0.0",
        },
        "paths": {},
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    schema = generate()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, sort_keys=True)
        f.write("\n")


if __name__ == "__main__":
    main()
