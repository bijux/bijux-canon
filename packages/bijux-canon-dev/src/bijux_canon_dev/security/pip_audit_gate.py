"""Pip audit gate helpers."""

from __future__ import annotations

import json
import os
from typing import Any

REPORT_PATH = os.getenv("PIPA_JSON", "")
IGNORE_IDS = set(filter(None, os.getenv("SECURITY_IGNORE_IDS", "").split()))
IS_STRICT = os.getenv("SECURITY_STRICT", "1") == "1"


def load_report(path: str) -> list[dict[str, Any]]:
    """Load report."""
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        message = f"ERROR: pip-audit JSON missing or unreadable at '{path}': {exc!s}"
        if IS_STRICT:
            print(message)
            raise SystemExit(2) from None
        print(message + " (non-strict: continuing with empty report)")
        return []

    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        dependencies = data.get("dependencies", [])
        if isinstance(dependencies, list):
            return dependencies

    message = f"ERROR: unexpected report format in '{path}'"
    if IS_STRICT:
        print(message)
        raise SystemExit(2)
    print(message + " (non-strict: continuing with empty report)")
    return []


def vulnerability_ids(vulnerability: dict[str, Any]) -> set[str]:
    """Handle vulnerability IDs."""
    ids: set[str] = set()
    vuln_id = vulnerability.get("id")
    if isinstance(vuln_id, str) and vuln_id:
        ids.add(vuln_id)
    aliases = vulnerability.get("aliases") or []
    if isinstance(aliases, list):
        for alias in aliases:
            if isinstance(alias, str) and alias:
                ids.add(alias)
    return ids


def primary_id(ids: set[str]) -> str:
    """Handle primary ID."""
    return sorted(ids)[0] if ids else "?"


def format_table(rows: list[tuple[str, str, str, str]]) -> str:
    """Format table."""
    header = ("Package", "Version", "ID", "FixVersions")
    widths = [len(cell) for cell in header]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    def format_row(columns: tuple[str, ...]) -> str:
        """Format row."""
        return "  ".join(
            column.ljust(widths[index]) for index, column in enumerate(columns)
        )

    lines = [format_row(header), "  ".join("-" * width for width in widths)]
    lines.extend(format_row(row) for row in rows)
    return "\n".join(lines)


def main() -> int:
    """Run the command-line entry point."""
    if IGNORE_IDS:
        print(f"INFO: ignoring IDs and aliases: {' '.join(sorted(IGNORE_IDS))}")

    dependencies = load_report(REPORT_PATH)
    if not dependencies:
        print("OK: no dependencies in report (or empty after parsing).")
        return 0

    ignored_count = 0
    remaining: list[tuple[str, str, str, str]] = []

    for dependency in dependencies:
        name = str(dependency.get("name", "?"))
        version = str(dependency.get("version", "?"))
        vulnerabilities = dependency.get("vulns") or []
        if not isinstance(vulnerabilities, list):
            continue
        for vulnerability in vulnerabilities:
            ids = vulnerability_ids(vulnerability)
            if ids & IGNORE_IDS:
                ignored_count += 1
                continue
            fix_versions = vulnerability.get("fix_versions") or []
            if not isinstance(fix_versions, list):
                fix_versions = []
            remaining.append(
                (
                    name,
                    version,
                    primary_id(ids),
                    ", ".join(fix_versions) if fix_versions else "-",
                )
            )

    if ignored_count:
        print(
            f"INFO: {ignored_count} vulnerability instance(s) matched ignore list and were skipped."
        )

    if not remaining:
        print("OK: 0 vulnerabilities remain after ignores.")
        return 0

    remaining.sort(key=lambda row: (row[0], row[2], row[1]))
    print(
        f"FAIL: {len(remaining)} vulnerability instance(s) remain after ignores.\n{format_table(remaining)}"
    )
    if IS_STRICT:
        print(f"STRICT: failing due to remaining vulnerabilities. See {REPORT_PATH}")
        return 1
    print(
        f"NON-STRICT: not failing despite remaining vulnerabilities. See {REPORT_PATH}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
