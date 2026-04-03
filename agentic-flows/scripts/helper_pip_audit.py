#!/usr/bin/env python3
"""Summarize pip-audit results and enforce ignore list if strict."""

from __future__ import annotations

import json
import os
from pathlib import Path


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


def main() -> int:
    pipa_json = Path(os.environ.get("PIPA_JSON", ""))
    strict = os.environ.get("SECURITY_STRICT", "1") == "1"
    ignore_ids = {
        item.strip()
        for item in os.environ.get("SECURITY_IGNORE_IDS", "").split()
        if item.strip()
    }

    if not pipa_json.exists():
        print("pip-audit JSON not found; skipping")
        return 0 if not strict else 1

    payload = _load_json(pipa_json)
    vulns = []
    for entry in payload.get("dependencies", []):
        for vuln in entry.get("vulns", []):
            vuln_id = vuln.get("id", "")
            if vuln_id and vuln_id not in ignore_ids:
                vulns.append(
                    (
                        entry.get("name", "<unknown>"),
                        vuln_id,
                        vuln.get("description", ""),
                    )
                )

    if not vulns:
        print("✔ pip-audit: no actionable vulnerabilities")
        return 0

    print("Vulnerabilities detected:")
    for name, vuln_id, desc in vulns:
        label = f"{name} {vuln_id}".strip()
        print(f"  - {label}: {desc}")

    return 1 if strict else 0


if __name__ == "__main__":
    raise SystemExit(main())
