---
title: Execution Model
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-07-21
---

# Execution Model

`bijux-canon-agent` coordinates specialized agents through a governed pipeline.
The orchestration layer owns ordering, stop conditions, convergence, trace
requirements, and finalization; individual agents remain bounded executors.

```mermaid
flowchart LR
    input["task goal + payload"]
    prepare["validate, fingerprint, plan, shard"]
    plan["PLAN"]
    execute["EXECUTE"]
    judge["JUDGE"]
    verify["VERIFY"]
    finalize["FINALIZE"]
    terminal{"terminal state"}
    done["DONE"]
    aborted["ABORTED"]

    input --> prepare --> plan --> execute --> judge --> verify --> finalize --> terminal
    terminal --> done
    terminal --> aborted
```

## Canonical Lifecycle

The standard pipeline is named `auditable-doc-pipeline`. Its normal transition
order is `INIT → PLAN → EXECUTE → JUDGE → VERIFY → FINALIZE → DONE`.
`ABORTED` is a terminal path for interruption or fatal failure.

Lifecycle metadata constrains which agent types may act:

| Lifecycle | Principal owner | Exit evidence |
| --- | --- | --- |
| `PLAN` | planner | completed execution plan |
| `EXECUTE` | reader, summarizer, stage runner, critique | stage results and execution traces |
| `JUDGE` | judge | recorded judgment |
| `VERIFY` | verifier | verification result or veto |
| `FINALIZE` | orchestrator | saved final record |

The controller validates transitions instead of inferring order from whichever
agent returns first.

## Preparation

Every run requires `task_goal`. A caller may supply `context_id`; otherwise it
is derived from the sorted input context. A cache key hashes all context fields
except `timestamp` and `nonce`, allowing observational timestamps to change
without invalidating equivalent work.

Preparation determines the required stages, shards large inputs, initializes
audit, revision, telemetry, warning, and status structures, and returns a cached
result when one exists. A cache hit is explicit in the result contract.

## Execution and Validation

Each shard runs the required stages and returns stage data, execution path,
audit trail, revisions, warnings, and terminal status. Shard results are merged
before the final result is extracted. A failed shard stops the current run and
produces the same structured failure shape as input or validation errors.

The merged result must pass goal-aware final validation before it can be
finalized. Validation issues do not disappear into logs: they change terminal
status, preserve warnings and an action plan, and prevent a successful result
from being cached.

## Convergence and Termination

Convergence tracks confidence and verdict history. Strategies can recognize
stability, confidence-only convergence, score behavior, and oscillation. The
chosen reason, decision type, iteration count, and convergence-window hash are
retained for replay.

Execution termination is classified as completed, convergence, failure, user
abort, or resource exhaustion. This is distinct from a role's pass/veto
decision: one explains why orchestration stopped, while the other records the
substantive decision.

## Finalization

Successful finalization closes telemetry, records pipeline counters, updates
the cache, persists the full pipeline result, and emits final result and trace
artifacts at the CLI boundary. A final result is derived back from its trace
before publication so decision, confidence, epistemic verdict, and stop reason
share one source.

The replay fingerprint covers the pipeline definition, contract version, and
configuration snapshot. Trace metadata separately retains prompt, model,
runtime, convergence, and input identity. Replayability requires deterministic
model settings, including zero temperature.

See [Data Contracts](../interfaces/data-contracts.md) for boundary shapes and
[Observability and Diagnostics](../operations/observability-and-diagnostics.md)
for evidence-led investigation.
