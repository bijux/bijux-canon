from __future__ import annotations

import argparse
import json
import sys

from bijux_canon_index.infra.adapters.vectorstore_registry import VECTOR_STORES
from bijux_canon_index.infra.embeddings.registry import EMBEDDING_PROVIDERS
from bijux_canon_index.infra.runners.registry import RUNNERS


def collect_report() -> dict[str, object]:
    groups = {
        "vectorstores": VECTOR_STORES.plugin_reports(),
        "embeddings": EMBEDDING_PROVIDERS.plugin_reports(),
        "runners": RUNNERS.plugin_reports(),
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
    lines = [
        "group | name | status | determinism | warning",
        "--- | --- | --- | --- | ---",
    ]
    groups = report["groups"]
    assert isinstance(groups, dict)
    for group, entries in groups.items():
        assert isinstance(entries, list)
        for entry in entries:
            lines.append(
                f"{group} | {entry.get('name')} | {entry.get('status')} | {entry.get('determinism')} | {entry.get('warning', '')}"
            )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate bijux-canon-index plugin contracts.")
    parser.add_argument("--format", choices=("json", "table"), default="json", help="Output format.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = collect_report()
    if args.format == "table":
        sys.stdout.write(render_table(report) + "\n")
        return 0
    sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
