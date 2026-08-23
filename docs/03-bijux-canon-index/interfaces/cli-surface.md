---
title: CLI Surface
audience: mixed
type: reference
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-07-21
---

# CLI Surface

The wheel registers the canonical Typer application as `bijux-canon-index`:

```bash
bijux-canon-index --help
bijux-canon-index --version
```

The equivalent module form is
`python -m bijux_canon_index.interfaces.cli.app`.

Global options precede the command: `--format json|table`, `--output PATH`,
`--config PATH`, `--trace`, `--quiet`, `--no-color`, and `--version`.

## Command Families

| Family | Commands | Purpose |
| --- | --- | --- |
| workspace | `init`, `capabilities`, `audit`, `doctor`, `validate` | prepare and inspect the execution environment |
| inventory | `list-artifacts`, `list-runs` | enumerate process artifacts or retained run directories |
| corpus | `ingest`, `materialize` | admit documents/vectors and bind them to an execution contract |
| execution | `execute`, `explain`, `replay`, `compare` | run and interpret retrieval decisions |
| vector database | `vdb status`, `vdb rebuild`, `vdb compact` | inspect and maintain configured vector stores |
| approximation | `nd tune`, `bench` | tune ANN policy and measure behavior |
| configuration | `config show` | render resolved configuration |
| diagnostics | `metrics-snapshot`, `debug-bundle` | capture runtime evidence |
| bundles | `artifact pack`, `artifact unpack` | move retained run evidence as an archive |

## Discover Before Mutating

```bash
python -m bijux_canon_index.interfaces.cli.app capabilities
python -m bijux_canon_index.interfaces.cli.app audit
python -m bijux_canon_index.interfaces.cli.app doctor
```

Capabilities report exact and ANN support, replay posture, selected backends,
metrics, and vector-store descriptors. Audit interprets those capabilities as
trust guarantees and limitations. Doctor checks configuration and environment
readiness. None of these commands creates a retrieval artifact.

## Ingest and Materialize

```bash
python -m bijux_canon_index.interfaces.cli.app ingest \
  --doc "signed records are retained for seven years" \
  --vector '[0.2, 0.8]' \
  --correlation-id retention-corpus

python -m bijux_canon_index.interfaces.cli.app materialize \
  --execution-contract deterministic \
  --index-mode exact
```

`ingest` accepts either an explicit vector or embedding configuration.
`--dry-run` renders resolved configuration without mutating state. Materialize
accepts `exact` or `ann`; the execution contract must agree with the selected
index behavior.

The default execution backend is SQLite at
`artifacts/bijux-canon-index/state/session.sqlite`. Separate invocations share
state only when they resolve the same backend and state path. Set
`BIJUX_CANON_INDEX_STATE_PATH` explicitly in automation; a relative default
changes meaning with the working directory. The explicit `memory` backend is
process-local. Vector-store configuration controls vector persistence and does
not replace the execution ledger.

## Execute

```bash
python -m bijux_canon_index.interfaces.cli.app execute \
  --vector '[0.2, 0.8]' \
  --artifact-id corpus-retention \
  --execution-contract deterministic \
  --execution-intent exact_validation \
  --execution-mode strict \
  --top-k 5 \
  --dry-run
```

Deterministic execution requires strict mode. Non-deterministic execution
requires bounded or exploratory mode, an execution budget, and explicit
randomness policy. ANN options cover profile, target recall, witnesses,
candidate limits, normalization, low-signal behavior, HNSW parameters, and
replay strictness. Use command-specific `--help` rather than copying an option
set between exact and approximate runs.

`--explain` resolves the first returned result. `--compare-to exact` requires
`--compare-artifact-id`. Standalone `explain` accepts `--result-id`; replay
requires the original request text and, for non-deterministic runs, replayable
randomness declarations.

## Output and Failure Semantics

JSON is the default output and is the safe automation format. `--output` writes
the rendered payload to a file; `--quiet` suppresses non-error output. Governed
refusals are emitted as structured error payloads before the mapped non-zero
exit. Unexpected exceptions exit with status `1`.

Capture the payload and exit status together. An empty or missing result list
must not be treated as equivalent to refusal, validation failure, or an
unavailable backend.
