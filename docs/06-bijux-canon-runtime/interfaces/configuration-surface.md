---
title: Configuration Surface
audience: mixed
type: reference
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-07-21
---

# Configuration Surface

Runtime behavior is declared by a flow manifest, a verification policy, an
execution mode, and persistence settings. The manifest and policy are JSON;
the CLI does not infer missing governance from ambient defaults.

## Effective workspace configuration

A local Runtime workspace has one versioned layout. Its manifest binds the
effective configuration identity, layout identity, locked embedding model,
CAS, DuckDB execution store, durable job store, persistent index root, locks,
staging, process state, VEX records, operations, backups, and the ordered
workspace-migration ledger. Runtime-owned state must remain below the workspace
root. A locked model directory may be external so one verified local cache can
serve multiple isolated workspaces.

Initialize or validate the layout before admitting documents:

```bash
bijux-canon-runtime init \
  --workspace /srv/bijux-canon/research \
  --model /srv/bijux-models/local-minilm-384/<locked-revision>
```

Add `--json` for a stable machine-readable result. A compatible repeat reports
`unchanged` without rewriting state. A partial workspace, incompatible version
or configuration, missing/corrupt model, external state override, unsafe path,
or unwritable activation is refused with a typed code and remediation. A known
older layout is preflighted, backed up, and migrated with manifest-last
activation; the result names the ordered migration and rollback identity. Init
never downloads a model and never silently repairs, downgrades, or replaces
unrecognized state.

The canonical environment names begin with `BIJUX_CANON_RUNTIME_`. In
particular, `WORKING_ROOT`, `DB_PATH`, `EMBEDDING_MODEL_PATH`, and
`RETRIEVAL_INDEX_PATH` participate in the recorded effective configuration.
Explicit `--workspace` and `--model` init arguments take precedence over their
environment counterparts; other configured fields remain part of the exact
workspace identity.

Each executable surface resolves this configuration once. Composition,
readiness, execution context, retrieval and agent adapters, inspection, and
configured backup construction consume that same immutable object; adapters do
not re-read environment paths during a run. Consequently, changing an
environment variable after admission cannot redirect retrieval, CAS, DuckDB,
jobs, model, index, or backup state for the admitted execution. A configured
backup derives its database, CAS, and default backup generation root from the
same workspace layout.

Readiness is capability-specific because ingest does not require an active
index or a loaded model, while retrieval does. Query it explicitly:

```bash
bijux-canon-runtime v2 ready --operation ingest
bijux-canon-runtime v2 ready --operation retrieve
bijux-canon-runtime v2 ready --operation research
```

`initialized` and `ingest` validate the workspace, exact DuckDB schema, CAS,
and write authority. `index` additionally verifies the locked local model.
`retrieve` also requires an active, integrity-checked generation built with
that exact model lock and dimension. `ask`, `research`, and `run` add provider
configuration only when the effective profile explicitly enables online
operation; the mandatory offline profile never requires provider credentials.
The HTTP equivalent is `GET /api/v2/ready?operation=<name>`.

## Flow manifest

A v1 manifest owns the identifiers and boundaries that must survive planning
and replay:

| Surface | Required declarations |
| --- | --- |
| Identity | `flow_id`, `tenant_id`, `flow_state` |
| Determinism | `determinism_level`, replay mode and acceptability, entropy budget, optional non-determinism intent |
| Replay | minimum claim overlap and maximum contradiction delta |
| Dataset | identifier, tenant, version, hash, state, storage URI, and deprecation permission |
| Topology | agents and `agent:dependency` edges |
| Authority | retrieval contracts and verification gates |

Unknown top-level keys are rejected. The loader fixes `spec_version` to `v1`
and requires an explicit determinism level; `default` is not accepted. Dataset
tenant and flow tenant must agree, agents must be unique, and dependencies must
form a reachable directed acyclic graph.

The checked-in minimal example is
`packages/bijux-canon-runtime/examples/boring/flow.json`.

## Verification policy

Live execution and replay require a policy JSON document. It declares the
verification level, failure mode, randomness tolerance, arbitration rule and
quorum, required evidence, maximum rule cost, rules, and the rule identifiers
that cause failure or escalation. The policy fingerprint is persisted with the
trace and compared during replay.

## Execution modes

| Mode | Behavior | Persistence |
| --- | --- | --- |
| `plan` | resolve and validate the execution plan without running it | none |
| `dry-run` | exercise the dry-run executor and produce a trace | DuckDB required |
| `live` | invoke runtime integrations, verify, and finalize | DuckDB and policy required |
| `observe` | verify a supplied observed run | Python API; store, policy, and observed run required |
| `unsafe` | execute through the live path with an explicit warning event | Python API requires store and policy |

The supported CLI surface is:

```text
bijux-canon-runtime run MANIFEST --policy POLICY --db-path RUNS.duckdb
bijux-canon-runtime replay MANIFEST --policy POLICY \
  --run-id RUN_ID --tenant-id TENANT --db-path RUNS.duckdb
bijux-canon-runtime inspect run RUN_ID --tenant-id TENANT --db-path RUNS.duckdb
```

All three accept `--json`; run and replay accept `--strict-determinism`.
Planning, dry-run, diff, failure explanation, and database validation are also
implemented as CLI commands but hidden from top-level help. `unsafe-run` is
present in the parser but cannot currently supply the verification policy that
runtime validation requires; do not depend on that CLI path.

## Python configuration and environment

`ExecutionConfig` additionally accepts artifact and execution stores, an
`ExecutionBudget`, observers, an observed run, parent and child flow IDs, a
resume run ID, verification and non-determinism policies, and strictness.
Executable modes use a write store; resumed execution also needs a read store.

Set `BIJUX_CANON_RUNTIME_STRICT=1` to force strict determinism. The legacy
`AGENTIC_FLOWS_STRICT=1` name is also recognized. Strict environment mode
rejects dry-run and unsafe execution. The legacy `AGENTIC_FLOWS_DB_PATH` is
still recognized at lower precedence than the canonical database setting.
