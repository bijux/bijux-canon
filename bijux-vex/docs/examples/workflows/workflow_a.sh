#!/usr/bin/env bash
set -euo pipefail

WORKDIR="$(mktemp -d)"
export BIJUX_VEX_STATE_PATH="$WORKDIR/session.sqlite"
export BIJUX_VEX_RUN_DIR="$WORKDIR/runs"
export PYTHONPATH="${PYTHONPATH:-}:src"

if [ -z "${PYTHON_BIN:-}" ]; then
  if [ -x ".venv/bin/python" ]; then
    PYTHON_BIN=".venv/bin/python"
  else
    PYTHON_BIN="$(command -v python3 || command -v python)"
  fi
fi

BIN="${PYTHON_BIN} -m bijux_vex.boundaries.cli.app"

$BIN init --config-path "$WORKDIR/bijux_vex.toml" --force
$BIN ingest --doc "hello" --vector "[0.0, 1.0, 0.0]" --vector-store memory
$BIN materialize --execution-contract deterministic --vector-store memory
$BIN execute --artifact-id art-1 --vector "[0.0, 1.0, 0.0]" \
  --execution-contract deterministic --execution-intent exact_validation \
  --vector-store memory
