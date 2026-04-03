#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_DIR="$(mktemp -d)"
VENV_DIR="${WORK_DIR}/venv"
TRACE_DIR="${WORK_DIR}/trace"

cleanup() {
  rm -rf "${WORK_DIR}"
}
trap cleanup EXIT

python3 -m venv "${VENV_DIR}"
"${VENV_DIR}/bin/pip" install --quiet --upgrade pip
"${VENV_DIR}/bin/pip" install --quiet bijux-agent

mkdir -p "${TRACE_DIR}"
export TRACE_DIR
"${VENV_DIR}/bin/python" - <<'PY'
import asyncio
import os
from pathlib import Path

from bijux_agent.reference.minimal import run_minimal
from bijux_agent.tracing.dry_run import write_dry_run_trace


async def main() -> None:
    result = await run_minimal(
        text="Hello world.",
        task_goal="summarize the input",
        context_id="quickstart",
    )
    assert result.get("result") is not None, "missing result"
    trace_path = Path(os.environ["TRACE_DIR"]) / "trace.json"
    write_dry_run_trace(trace_path)
    assert trace_path.exists(), "missing trace"


asyncio.run(main())
print("quickstart ok")
PY
