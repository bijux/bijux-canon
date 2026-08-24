---
title: Interfaces
audience: mixed
type: index
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-08-25
---

# Interfaces

Runtime interfaces carry authority. A caller must preserve tenant, manifest,
plan, dataset, policy, environment, trace, artifact, entropy, and replay
identity rather than reducing a governed run to its final payload.

## Surface map

| Surface | Availability | Authority contract |
| --- | --- | --- |
| Python | complete execution surface | manifests, plans, execution configuration, stores, policies, results, replay |
| CLI | plan, dry run, live run, replay, inspect, diff, failure explanation, database validation | JSON/plain output, exit classes, DuckDB path, tenant and run identity |
| HTTP v2 | complete application-service surface | versioned requests, durable jobs, bounded reads, typed failures, and shared workspace authority |
| HTTP v1 compatibility module | probes plus schema-only run/replay | explicit legacy host; run and replay return `501 Not Implemented` |
| DuckDB store | local typed persistence | runs, datasets, steps, events, checkpoints, artifacts, evidence, claims, tools, entropy, finalization |
| artifact store | payload persistence | immutable identity, hash, parentage, producer, tenant, and scope |
| versioned schemas | compatibility boundary | HTTP payloads, database migrations, and schema hashes |

## Flow contract path

```mermaid
sequenceDiagram
    participant Caller
    participant Runtime
    participant Executors
    participant Verifier
    participant Store
    Caller->>Runtime: manifest + policy + mode + store
    Runtime->>Runtime: resolve plan and authority
    Runtime->>Executors: ordered governed steps
    Executors-->>Runtime: events, artifacts, evidence, claims
    Runtime->>Verifier: results + gates + budgets
    Verifier-->>Runtime: findings + arbitration
    Runtime->>Store: finalized trace and projections
    Runtime-->>Caller: FlowRunResult or classified failure
```

## Current interface constraints

- Plan mode returns no run ID or trace because it allocates no execution.
- Live JSON output currently omits the run ID; plain output exposes it, after
  which `inspect run --json` can retrieve the retained trace.
- `diff run` reports differences without failing the process. Automation must
  evaluate the payload.
- `validate db` proves schema initialization and readability, not row-level
  integrity or semantic replayability.
- `unsafe-run` is parsed but cannot currently supply its required verification
  policy through the CLI. Use the governed Python surface when that explicit
  reduced-guarantee mode is necessary.
- Several callable CLI commands are suppressed from top-level help.
- The v2 server is local-first and supplies no authentication, tenant
  authorization, sandboxing, TLS termination, or multi-writer coordination.

## Use the least-authoritative surface

Runtime separates inspection from execution so callers do not need to grant
effect authority merely to understand a flow or retained run:

| Need | Surface | Authority consumed | Result boundary |
| --- | --- | --- | --- |
| prove the service process is reachable | HTTP v2 liveness | none | liveness only |
| prove an operation/profile is configured | HTTP v2 readiness or capabilities | read-only workspace inspection | declared capability, not a successful workflow |
| inspect dependency order and replay declarations | CLI or Python plan | manifest resolution only | plan and `plan_hash`; no run ID or trace |
| inspect retained history | CLI `inspect`, failure explanation, or typed readers | tenant-scoped read access | stored projection; payload availability must be checked separately |
| compare retained runs | CLI diff or analysis modules | read access to both records | reported differences; process exit does not decide acceptability |
| execute or resume effects | governed Python or CLI run surface | flow authority, policy, stores, budgets and executor bindings | finalized, arbitrated run or classified failure |
| request a local service run or replay | HTTP v2 | workspace, durable job, operation budget, and idempotency authority | bounded job status followed by deliberate result/inspection reads |

Start with plan or read-side inspection whenever the question does not require
new effects. Moving to live execution is a new authority decision: the caller
must provide working adapters, storage, verification policy, and effect
controls. A successful health check, readable database, or valid manifest does
not confer any of those capabilities.

## Assemble the authority packet

Before an executable call, retain the inputs that authorize work; after the
call, require the records that prove how that authority was used:

| Authority concern | Required before execution | Required before accepting the result |
| --- | --- | --- |
| ownership | flow, tenant, manifest state and authority context | identical flow/tenant identity on trace, store rows and artifacts |
| data | dataset ID, version, digest, state, location and deprecation policy | observed dataset identity and any admitted evolution decision |
| plan | resolved dependencies, ordered work, environment fingerprint and `plan_hash` | every executed or skipped operation accounted for against that plan |
| variability | determinism level, nondeterminism intent, entropy budget and allowed variance | measured entropy use, warnings and budget disposition |
| verification | declared gates, rule configuration and arbitration policy | immutable findings, separate arbitration decision and certifiability |
| effects | mode, executor bindings, credentials/capabilities and idempotency posture | causal events, effect receipts, failures and recovery disposition |
| persistence | execution-store and artifact-store identities | finalized run record plus resolvable payload hashes and lineage |
| replay | original envelope and acceptability policy | semantic diff, verdict, reason and compared identities |

If a live lower-package callable cannot be resolved, the authority packet is
incomplete and execution must fail at that integration boundary. A plan, an
installed dependency, or a compatibility alias cannot stand in for an
executor binding. Likewise, DuckDB metadata cannot stand in for artifact or
evidence payloads that the artifact store no longer resolves.

## Compatibility boundaries

Manifest meaning, determinism levels, authority headers, verification rules,
arbitration, trace finalization, event order, entropy accounting, replay
acceptability, storage normalization, migrations, and schema hashes all affect
caller-visible authority. A storage migration can be breaking even when the
Python dataclasses do not change.

## Contract index

| Need | Guide |
| --- | --- |
| Operate execution and read-side commands | [CLI surface](cli-surface.md) |
| Integrate health, readiness, or future flow routes | [API surface](api-surface.md) |
| Configure stores, strictness, policy, and budgets | [Configuration surface](configuration-surface.md) |
| Construct manifests, plans, traces, artifacts, and verification records | [Data contracts](data-contracts.md) |
| Accept persisted runs and payloads | [Artifact contracts](artifact-contracts.md) |
| Compose public runtime modules | [Public imports](public-imports.md) |
| Follow plan, live, inspect, and replay journeys | [Operator workflows](operator-workflows.md) |
| Evaluate authority-compatible evolution | [Compatibility commitments](compatibility-commitments.md) |
| Start from executable examples | [Entrypoints and examples](entrypoints-and-examples.md) |
