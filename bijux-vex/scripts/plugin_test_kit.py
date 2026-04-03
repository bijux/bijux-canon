# SPDX-License-Identifier: MIT
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

import argparse
import json
import sys

from bijux_vex.infra.adapters.vectorstore_registry import VECTOR_STORES
from bijux_vex.infra.embeddings.registry import EMBEDDING_PROVIDERS
from bijux_vex.infra.runners.registry import RUNNERS


def _collect() -> dict[str, object]:
    return {
        "vectorstores": VECTOR_STORES.plugin_reports(),
        "embeddings": EMBEDDING_PROVIDERS.plugin_reports(),
        "runners": RUNNERS.plugin_reports(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Bijux-Vex plugin contracts.")
    parser.add_argument(
        "--format",
        choices=("json", "table"),
        default="json",
        help="Output format",
    )
    args = parser.parse_args()
    report = _collect()
    if args.format == "table":
        lines = [
            "group | name | status | determinism | warning",
            "--- | --- | --- | --- | ---",
        ]
        for group, entries in report.items():
            for entry in entries:
                lines.append(
                    f"{group} | {entry.get('name')} | {entry.get('status')} | {entry.get('determinism')} | {entry.get('warning', '')}"
                )
        sys.stdout.write("\n".join(lines) + "\n")
        return 0
    sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
