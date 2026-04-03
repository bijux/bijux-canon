#!/usr/bin/env python3
"""Ensure only expected directories remain after running tests."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ALLOWED_DIRS = {
    ".venv/",
    ".pytest_cache/",
    ".benchmarks/",
    ".ruff_cache/",
    "../../artifacts/bijux-canon-agent/",
    "src/bijux_canon_agent/agents/critique/",
    "src/bijux_canon_agent/agents/file_reader/",
    "src/bijux_canon_agent/agents/judge/",
    "src/bijux_canon_agent/agents/kernel/",
    "src/bijux_canon_agent/agents/planner/",
    "src/bijux_canon_agent/agents/summarizer/",
    "src/bijux_canon_agent/agents/workflow_executor/",
    "src/bijux_canon_agent/agents/validator/",
    "src/bijux_canon_agent/agents/verifier/",
    "src/bijux_canon_agent/application/",
    "src/bijux_canon_agent/application/orchestration/",
    "src/bijux_canon_agent/pipeline/control/",
    "src/bijux_canon_agent/pipeline/convergence/",
    "src/bijux_canon_agent/pipeline/execution/",
    "src/bijux_canon_agent/pipeline/results/",
    "src/bijux_canon_agent/pipeline/tracing/",
    "src/bijux_canon_agent/examples/",
    "src/bijux_canon_agent/api/",
    "src/bijux_canon_agent/api/v1/",
    "src/bijux_canon_agent/interfaces/",
    "src/bijux_canon_agent/interfaces/cli/",
    "src/bijux_canon_agent/observability/",
    "src/bijux_canon_agent/support/",
    "tests/snapshots/",
    "docs/",
    "docs/architecture/",
    "docs/agents/",
    "docs/cli/",
    "docs/concepts/",
    "docs/configuration/",
    "docs/execution-model/",
    "docs/examples/",
    "docs/governance/",
    "docs/invariants/",
    "docs/tracing-replay/",
    "examples/",
    "tests/unit/",
    "tests/e2e/",
    "tests/invariants/",
    "tests/integration/",
    "tests/api/",
    "tests/stubs/",
    "tests/utils/",
}


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2] / "packages" / "bijux-canon-agent"
    completed = subprocess.run(
        ["git", "ls-files", "--others", "--directory", "--exclude-standard"],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    tracked = completed.stdout.splitlines()
    offenders = [
        path for path in tracked if path.endswith("/") and not any(
            path.startswith(prefix) for prefix in ALLOWED_DIRS
        )
    ]
    if offenders:
        print("error: unexpected untracked directories found:")
        for path in offenders:
            print(f"  - {path}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
