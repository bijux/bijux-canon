---
title: Entrypoints and Examples
audience: mixed
type: how-to
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-07-22
---

# Entrypoints and Examples

Use Python plan mode to resolve a manifest without execution, the console
command for persisted run operations, and the HTTP surface only with its
experimental implementation status understood.

## Python: resolve a plan safely

The default `execute_flow(manifest)` call selects live, strict execution and is
not a dependency-free preview. A safe minimal integration declares plan mode:

```python
from pathlib import Path

from bijux_canon_runtime import RunMode, execute_flow
from bijux_canon_runtime.application.execute_flow import ExecutionConfig
from bijux_canon_runtime.interfaces.cli.manifest_loader import load_manifest

manifest = load_manifest(Path("flow.json"))
result = execute_flow(
    manifest=manifest,
    config=ExecutionConfig(
        mode=RunMode.PLAN,
        determinism_level=manifest.determinism_level,
    ),
)

print(result.resolved_flow.manifest.flow_id)
assert result.trace is None
assert result.run_id is None
```

Executable modes additionally need an execution store and, where required by
the mode, verification and non-determinism policy. Supply those dependencies
through `ExecutionConfig`; do not rely on defaults to invent runtime authority.

## CLI: plan before execution

From a repository checkout, plan the maintained example directly:

```bash
uv run bijux-canon-runtime plan \
  packages/bijux-canon-runtime/examples/boring/flow.json \
  --json
```

Plan mode validates and resolves the manifest without executing steps. The
manifest must declare determinism, replay acceptability, entropy budget,
replay envelope, dataset identity, agents, retrieval contracts, and
verification gates.

For an installed distribution, copy the example manifest into an
application-owned location and invoke the same boundary:

```bash
bijux-canon-runtime plan flow.json --json
```

Treat these output fields as a pre-execution review record:

| Field group | Review before execution |
| --- | --- |
| flow and tenant | authority belongs to the intended caller and namespace |
| dataset descriptor | ID, version, hash, lifecycle state, and URI are the intended inputs |
| steps and dependencies | order and agent identities match the declared flow |
| determinism and entropy | permitted variance and exhaustion behavior match operational policy |
| replay envelope | comparison thresholds were fixed before any output was observed |
| environment and plan fingerprints | the resolved contract can be compared with the eventual run |

Plan success is intentionally weaker than executable readiness. It does not
open the DuckDB store, load the live lower-package callables, exercise an
external effect, arbitrate verification, or persist a replayable record.

## CLI: execute and persist a governed run

```bash
bijux-canon-runtime run flow.json \
  --policy policy.json \
  --db-path artifacts/bijux-canon-runtime/runs.duckdb \
  --strict-determinism
```

Plain output includes the run identifier that addresses persisted state. The
current live `--json` rendering omits that identifier, so capture it from plain
output before using `inspect run --json` for the complete persisted trace.

## CLI: inspect, replay, and compare

```bash
bijux-canon-runtime inspect run <run-id> \
  --tenant-id <tenant-id> \
  --db-path artifacts/bijux-canon-runtime/runs.duckdb \
  --json

bijux-canon-runtime replay flow.json \
  --policy policy.json \
  --run-id <run-id> \
  --tenant-id <tenant-id> \
  --db-path artifacts/bijux-canon-runtime/runs.duckdb \
  --strict-determinism \
  --json

bijux-canon-runtime diff run <first-run-id> <second-run-id> \
  --tenant-id <tenant-id> \
  --db-path artifacts/bijux-canon-runtime/runs.duckdb \
  --json
```

Replay exits with contract-violation status when a semantic diff is present.
Use `explain failure` to retrieve the last persisted failure event and
`validate db` to confirm that an execution store is readable. `plan`,
`dry-run`, `unsafe-run`, `diff`, `explain`, and `validate` are parsed but
currently suppressed from top-level help output. `unsafe-run` cannot yet reach
execution through the CLI because unsafe mode requires a verification policy
and that subcommand exposes no `--policy` option.

## HTTP: current implementation boundary

The FastAPI module can expose liveness and storage readiness:

```bash
AGENTIC_FLOWS_DB_PATH=artifacts/bijux-canon-runtime/runs.duckdb \
  uvicorn bijux_canon_runtime.api.v1.app:app \
  --host 127.0.0.1 --port 8000

curl --fail-with-body http://127.0.0.1:8000/api/v1/health
curl --fail-with-body http://127.0.0.1:8000/api/v1/ready
```

The module is explicitly marked experimental and not production-ready.
`POST /api/v1/flows/run` and `POST /api/v1/flows/replay` validate their request
envelopes and required runtime headers, then currently return `501 Not
Implemented`. Do not route production execution through those endpoints or
describe the checked-in schema as proof of implemented HTTP execution.

The authoritative boundary shape is the checked-in
[`v1 schema`](https://github.com/bijux/bijux-canon/blob/main/apis/bijux-canon-runtime/v1/schema.yaml),
while the console and Python paths remain the implemented execution surfaces.
