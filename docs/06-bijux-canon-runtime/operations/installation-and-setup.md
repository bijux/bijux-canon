---
title: Installation and Setup
audience: mixed
type: how-to
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-08-24
---

# Installation and Setup

`bijux-canon-runtime` supports Python 3.11 through 3.14. The base distribution
includes DuckDB persistence and depends on the canonical ingest, index, reason,
and agent packages so runtime contracts can bind their artifacts.

```mermaid
flowchart LR
    P[Install canonical runtime] --> M[Declare manifest and policy]
    M --> L[Resolve plan]
    L --> S[Create governed store]
    S --> R[Execute and inspect run]
    R --> V[Validate persistence and replay inputs]
```

## Install

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install bijux-canon-runtime
```

The base installation fulfills `offline-lexical`. Choose extras by the public
operation profile rather than installing the development environment:

| Product profile | Installation | Installed capability |
| --- | --- | --- |
| offline lexical | `bijux-canon-runtime` | SQLite FTS5 ingest, index, retrieval, answer, and research without a model |
| local exact, ANN, or hybrid | `bijux-canon-runtime[local-cpu]` | NumPy, CPU FAISS, sentence-transformers, and PyTorch |
| HTTP | `bijux-canon-runtime[api]` | FastAPI, Starlette, and Uvicorn |

On Linux CPU hosts, install PyTorch from its CPU wheel index before resolving
`local-cpu`. This is required because the default Linux PyTorch wheel channel
may include CUDA runtime distributions even when Runtime selects `device=cpu`:

```bash
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
python -m pip install 'bijux-canon-runtime[local-cpu]'
```

On macOS, the native `local-cpu` profile is supported on Python 3.11. FAISS
1.7.4 is constrained with NumPy 1.26 because that combination can share a
process with PyTorch safely; newer FAISS macOS wheels abort after duplicate
OpenMP initialization, and FAISS 1.7.4 has no Python 3.12+ wheel. The base
lexical and `api` installations continue to support Python 3.11 through 3.14.

The `bijux-cli` dependency publishes a Linux x86_64 wheel. On Linux ARM64,
install a C build toolchain before installing Runtime so pip can build that
dependency from its source distribution. For example, Debian and Ubuntu hosts
can use `sudo apt-get install build-essential`.

Verify the stable package root and CLI:

```bash
python -c "from bijux_canon_runtime import FlowManifest, RunMode, execute_flow; print(RunMode.PLAN)"
bijux-canon-runtime --help
```

## Initialize a local workspace

An offline lexical workspace does not need an embedding model:

```bash
WORKSPACE=/srv/bijux-canon/research
bijux-canon-runtime init --workspace "$WORKSPACE" --json
bijux-canon-runtime v2 ready \
  --operation index \
  --profile offline-lexical
```

Omitting `--model` records that the model capability is not configured; it does
not access a model cache or network. Lexical ingest, index, retrieval, answer,
and research requests remain usable in that workspace.

For a local dense or hybrid profile, materialize a supported embedding model
into a durable local cache first. The model directory passed to Runtime is the
revision directory containing the canonical `model.lock.json` and all artifacts
named by that lock. Workspace initialization is offline and verifies every
locked artifact.

```bash
WORKSPACE=/srv/bijux-canon/research
MODEL=/srv/bijux-models/local-minilm-384/<locked-revision>

bijux-canon-runtime init \
  --workspace "$WORKSPACE" \
  --model "$MODEL" \
  --json
```

The first call atomically activates a complete workspace. Repeating the same
command returns `unchanged` and leaves all state bytes untouched. Do not
pre-create the workspace directory: an existing directory without the
canonical manifest is treated as partial state and refused rather than filled
in. Preserve the whole workspace for restart, inspection, replay, and backup;
the DuckDB file alone is not the complete authority.

### Workspace migration and rollback

Stop Runtime workers before running `init` against an older workspace. The
current Runtime recognizes exact version-1 and version-2 layouts, validates the
manifest, model, DuckDB migrations, durable-job schema, CAS, and index structure
before changing anything, and creates content-bound rollback generations below
`backups/workspace-migrations/generations/`. Version 2 to version 3 binds the
Index-owned retrieval policy into effective configuration identity; its backup
contains both the source `workspace.json` and `workspace-migrations.json`.
Version 1 workspaces apply the two ordered migrations. Runtime writes the
updated migration ledger first and activates the version-3 `workspace.json`
last. A successful upgrade reports `migrated`, the applied migration identities,
and the exact rollback backup path. Repeating `init` does not append or reapply
a migration.

If the process stops after ledger publication but before manifest activation,
repeat the same `init` command. Runtime verifies the source manifest and
rollback backup identities and resumes the same migration. Do not delete the
ledger or edit either checksum. A newer workspace or a layout older than the
supported migration floor is refused before a backup or state mutation.

For an immediate rollback before admitting new work, stop Runtime and preserve
the failed/upgraded workspace. For version 3 to version 2, verify the reported
backup generation and restore both its exact `workspace.json` and
`workspace-migrations.json`, then reopen with the prior Runtime release. A
version-1 rollback similarly restores its manifest and removes the version-2
ledger that did not exist at the source version. If any work was admitted after
migration, restore a complete pre-upgrade workspace backup instead; migration
rollback generations cover workspace authority, not later application writes.

Verify the exact operation boundary before submitting work:

```bash
BIJUX_CANON_RUNTIME_WORKING_ROOT="$WORKSPACE" \
BIJUX_CANON_RUNTIME_EMBEDDING_MODEL_PATH="$MODEL" \
  bijux-canon-runtime v2 ready \
    --operation retrieve \
    --profile local-hybrid-ann
```

A new workspace is ready for ingest before it has an index. Profile-specific
readiness reports only shared workspace dependencies for `offline-lexical`;
the supplied lexical artifact is validated immediately before submission.
Hybrid readiness additionally requires a verified dense generation and model.

Install `bijux-canon` or `agentic-flows` only when an application still needs a
compatibility import or command. New code should install the canonical runtime.

## Start with the Checked-In Example

From a repository checkout, the `boring` example provides a strict manifest
and baseline policy:

```bash
make install
bijux-canon-runtime plan \
  packages/bijux-canon-runtime/examples/boring/flow.json \
  --json
```

Plan mode is the safest setup check. It validates and resolves the flow without
executing steps, writing a trace, or allocating a run identifier.

The command determines how much authority is exercised:

| Command | Effects and persistence | Appropriate use |
| --- | --- | --- |
| `plan` | resolves contracts without executing steps or writing a run | manifest and dependency review |
| `dry-run` | exercises dry-run contracts against an explicit store without live authority | execution-shape and refusal checks |
| `run` | performs governed live execution with the supplied verification policy | accepted operational work |
| `unsafe-run` | enters the explicit unsafe execution mode | isolated evidence for behavior that cannot meet the governed live posture |
| `replay` | executes against a persisted envelope and compares the new record with the original | declared replay-acceptability checks |

`unsafe-run` is not a faster form of `run`. Its mode is part of the retained
record and prevents unsafe execution from being presented as governed live
authority.

For an installed-wheel integration, create equivalent application-owned
`flow.json` and `policy.json` files from the
[data contracts](../interfaces/data-contracts.md). Do not copy identifiers,
dataset hashes, storage URIs, or tenant values from an example into production
without replacing them with real governed values.

## Create the Execution Store

Choose a durable path explicitly:

```bash
mkdir -p artifacts/bijux-canon-runtime

bijux-canon-runtime run \
  packages/bijux-canon-runtime/examples/boring/flow.json \
  --policy packages/bijux-canon-runtime/examples/boring/policy.json \
  --db-path artifacts/bijux-canon-runtime/runs.duckdb \
  --strict-determinism \
  --json
```

The operating-system user needs create, read, write, replace, and lock-file
permissions in the database directory. The execution store supports a
single-writer posture; do not point independent runtime processes at the same
file for concurrent mutation.

Validate the store before using it for inspection or replay:

```bash
bijux-canon-runtime validate db \
  --db-path artifacts/bijux-canon-runtime/runs.duckdb \
  --json
```

## Inspect the First Run

Use the `run_id` and tenant returned by execution:

```bash
bijux-canon-runtime inspect run <run-id> \
  --tenant-id tenant-a \
  --db-path artifacts/bijux-canon-runtime/runs.duckdb \
  --json
```

Confirm that the trace is finalized, dataset identity matches the manifest,
and the arbitration, entropy, artifact, evidence, and event records agree with
the intended authority.

## Replay Under the Original Identity

Replay requires the current manifest and policy as well as the original run
and tenant identities:

```bash
bijux-canon-runtime replay \
  packages/bijux-canon-runtime/examples/boring/flow.json \
  --policy packages/bijux-canon-runtime/examples/boring/policy.json \
  --run-id <run-id> \
  --tenant-id tenant-a \
  --db-path artifacts/bijux-canon-runtime/runs.duckdb \
  --strict-determinism \
  --json
```

A clean replay means the comparison found no difference outside the declared
contract. A contract-violation exit identifies a blocking difference; retain
its reason code and JSON diff. Replay does not establish that external facts
remain true, and an acceptability threshold does not erase an observed drift.

## HTTP Health and Readiness

The API extra supports operational probes:

```bash
python -m pip install 'bijux-canon-runtime[api]'

AGENTIC_FLOWS_DB_PATH=artifacts/bijux-canon-runtime/runs.duckdb \
  uvicorn bijux_canon_runtime.api.v1.app:app \
  --host 127.0.0.1 --port 8000
```

```bash
curl --fail-with-body http://127.0.0.1:8000/api/v1/health
curl --fail-with-body http://127.0.0.1:8000/api/v1/ready
```

Readiness checks storage; it does not make HTTP run or replay operational.
Those endpoints currently return `501 Not Implemented` after validating their
request boundary.

## Repository Checkout

```bash
make install
make -f "$PWD/makes/packages/bijux-canon-runtime.mk" \
  -C packages/bijux-canon-runtime help
make test PACKAGE=bijux-canon-runtime
make docs-check
```

Package Makefiles are repository profiles under `makes/packages/`; the package
directory does not contain a standalone Makefile. Use the root dispatcher for
normal checks and the explicit profile form when inspecting package targets.
The absolute profile path remains valid after Make applies `-C`.

Use package and documentation checks for the first feedback loop. Broader
repository lanes are appropriate only when a change crosses shared contracts.

## Setup Checklist

- The stable root imports and CLI resolve from the expected environment.
- Planning succeeds before any live authority is granted.
- Manifest, dataset, policy, and tenant identities are application-owned and
  explicit.
- The DuckDB directory has durable storage and one-writer coordination.
- A completed run can be inspected and the database passes schema validation.
- HTTP clients are not routed to the unimplemented run or replay endpoints.

Continue with [state and persistence](../architecture/state-and-persistence.md)
and [entrypoint examples](../interfaces/entrypoints-and-examples.md).
