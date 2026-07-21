---
title: Capability Map
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-07-21
---

# Capability Map

`bijux-canon-agent` provides role-based workflow control whose lifecycle,
decisions, convergence, termination, and trace can be inspected independently
of the final text. Provider access is an adapter capability, not the source of
orchestration authority.

```mermaid
flowchart LR
    input["task goal + context"]
    definition["pipeline definition"]
    lifecycle["owned transitions"]
    roles["bounded role calls"]
    merge["shard merge + validation"]
    converge["convergence + termination"]
    output["PipelineResult + RunTrace"]

    input --> definition --> lifecycle --> roles --> merge --> converge --> output
```

## Workflow capabilities

| Capability | Owning area | Produced evidence |
| --- | --- | --- |
| Strict role contracts | `contracts/` | immutable inputs, outputs, errors, plans, and runtime records |
| Canonical pipeline definition | `pipeline/definition.py` and canonical pipeline | role eligibility, lifecycle phases, transitions, terminal states |
| Lifecycle control | `pipeline/control/` | validated transition, stop reason, causal order |
| Role registry | `pipeline/agent_registry.py` | explicit role-to-implementation resolution |
| Bounded role execution | `agents/` | role output or typed error with call metadata |
| Input sharding and merge | `pipeline/execution/` and `pipeline/results/` | shard status, merged result, warnings, revisions, action plan |
| Goal-aware final validation | result finalization | success/failure state that cannot be cached as success when invalid |
| Cache selection | preparation and runtime support | context-derived key and explicit cache-hit state |

## Decision and evidence capabilities

| Capability | Owning area | Produced evidence |
| --- | --- | --- |
| Convergence evaluation | `pipeline/convergence/` | strategy, window, snapshots, hash, verdict history, reason |
| Termination classification | `pipeline/termination.py` | completion, convergence, failure, abort, or exhaustion |
| Epistemic disposition | pipeline epistemic models | pass/veto and epistemic status separate from execution success |
| Versioned trace | `traces/` | header metadata, ordered entries, run fingerprint, replay fields |
| Trace validation | `pipeline/trace_validation/` | ordering, completeness, epistemic, and replayability findings |
| Trace reconstruction | replay support | terminal result projection and documented summary parity |
| Structured observability | `observability/` and execution telemetry | stages, shards, duration, counters, contextual logs |
| Provider adapters | `llm/` | provider/model identity, prompt/model hashes, usage, result or error |

## Role capabilities

The package includes bounded roles for file reading, summarization, critique,
validation, stage execution, planning, judging, and verification. A role
supplies local behavior within the active lifecycle phase. It cannot override
the controller, invent a terminal transition, or silently become runtime
authority.

## Public boundary

Python exposes the complete composition model. The CLI runs files or immediate
directory entries and publishes result/trace files. HTTP v1 deliberately runs
one fixed offline `simple`/`extractive` pipeline. Source-level model adapters do
not expand that versioned HTTP contract.

Convergence proves only that a configured condition was observed. Trace replay
proves retained fields are coherent. Neither establishes model correctness or
recreates a remote provider's historical serving environment.

See [Invariants](../quality/invariants.md) for lifecycle and trace laws and
[Known limitations](../quality/known-limitations.md) for model, convergence,
replay, credential, and hosting boundaries.
