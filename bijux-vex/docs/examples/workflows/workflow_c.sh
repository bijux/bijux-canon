#!/usr/bin/env bash
set -euo pipefail

WORKDIR="$(mktemp -d)"
export BIJUX_VEX_STATE_PATH="$WORKDIR/session.sqlite"
export BIJUX_VEX_RUN_DIR="$WORKDIR/runs"
export BIJUX_VEX_BACKEND="hnsw"
export BIJUX_VEX_HNSW_PATH="$WORKDIR/hnsw_index"
export PYTHONPATH="${PYTHONPATH:-}:src"

if [ -z "${PYTHON_BIN:-}" ]; then
  if [ -x ".venv/bin/python" ]; then
    PYTHON_BIN=".venv/bin/python"
  else
    PYTHON_BIN="$(command -v python3 || command -v python)"
  fi
fi

BIN="${PYTHON_BIN} -m bijux_vex.boundaries.cli.app"

if ! $PYTHON_BIN - <<'PY'; then
import sys
try:
    import faiss  # noqa: F401
except Exception:
    print("faiss not installed; skipping workflow_c")
    sys.exit(1)
PY
  exit 0
fi

$BIN init --config-path "$WORKDIR/bijux_vex.toml" --force
$BIN ingest --doc "hello ann" --vector "[0.0, 1.0, 0.0]" \
  --vector-store faiss --vector-store-uri "$WORKDIR/index.faiss"
$BIN materialize --execution-contract non_deterministic --index-mode ann \
  --vector-store faiss --vector-store-uri "$WORKDIR/index.faiss"
$BIN execute --artifact-id art-1 --vector "[0.0, 1.0, 0.0]" \
  --execution-contract non_deterministic --execution-intent exploratory_search \
  --execution-mode bounded --randomness-seed 42 --randomness-sources "ann_probe" \
  --nd-build-on-demand \
  --vector-store faiss --vector-store-uri "$WORKDIR/index.faiss"
