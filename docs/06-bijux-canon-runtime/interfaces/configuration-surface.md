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
rejects dry-run and unsafe execution. `AGENTIC_FLOWS_DB_PATH` configures the
DuckDB file checked by HTTP readiness; it does not configure CLI commands.
