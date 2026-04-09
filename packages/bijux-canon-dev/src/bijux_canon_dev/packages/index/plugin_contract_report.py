"""Plugin contract report helpers."""

from __future__ import annotations

import argparse
from importlib import import_module
import json
import sys
from typing import Any


def _load_registry(module_path: str, attr_name: str) -> Any:
    """Load a plugin registry object from bijux-canon-index lazily."""
    module = import_module(module_path)
    registry = getattr(module, attr_name, None)
    if registry is None:
        raise RuntimeError(f"missing registry {attr_name!r} in module {module_path!r}")
    return registry


def collect_report() -> dict[str, object]:
    """Handle collect report."""
    vector_stores = _load_registry(
        "bijux_canon_index.infra.adapters.vectorstore_registry", "VECTOR_STORES"
    )
    embedding_providers = _load_registry(
        "bijux_canon_index.infra.embeddings.registry", "EMBEDDING_PROVIDERS"
    )
    runners = _load_registry("bijux_canon_index.infra.runners.registry", "RUNNERS")
    groups = {
        "vectorstores": vector_stores.plugin_reports(),
        "embeddings": embedding_providers.plugin_reports(),
        "runners": runners.plugin_reports(),
    }
    entries = [entry for group_entries in groups.values() for entry in group_entries]
    failures = [entry for entry in entries if entry.get("status") != "loaded"]
    return {
        "summary": {
            "group_count": len(groups),
            "plugin_count": len(entries),
            "loaded_count": len(entries) - len(failures),
            "issue_count": len(failures),
        },
        "groups": groups,
    }


def render_table(report: dict[str, object]) -> str:
    """Render table."""
    lines = [
        "group | name | status | determinism | warning",
        "--- | --- | --- | --- | ---",
    ]
    groups = report["groups"]
    if not isinstance(groups, dict):
        raise TypeError("report groups must be a dictionary")
    for group, entries in groups.items():
        if not isinstance(entries, list):
            raise TypeError(f"report group {group!r} must contain a list of entries")
        lines.extend(
            [
                f"{group} | {entry.get('name')} | {entry.get('status')} | {entry.get('determinism')} | {entry.get('warning', '')}"
                for entry in entries
            ]
        )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    """Parse args."""
    parser = argparse.ArgumentParser(
        description="Validate bijux-canon-index plugin contracts."
    )
    parser.add_argument(
        "--format", choices=("json", "table"), default="json", help="Output format."
    )
    return parser.parse_args()


def main() -> int:
    """Run the command-line entry point."""
    args = parse_args()
    report = collect_report()
    if args.format == "table":
        sys.stdout.write(render_table(report) + "\n")
        return 0
    sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
