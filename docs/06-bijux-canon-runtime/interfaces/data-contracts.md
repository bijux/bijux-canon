---
title: Data Contracts
audience: mixed
type: reference
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-07-21
---

# Data Contracts

Runtime authority begins with a manifest, becomes a resolved plan, and ends as
a finalized trace plus governed evidence. Policy values remain part of that
chain; they are not ambient configuration that can be omitted from replay.

```mermaid
flowchart LR
    Manifest[FlowManifest] --> Validate[contract validation]
    Validate --> Plan[ExecutionPlan]
    Policy[verification and non-determinism policies] --> Execute
    Plan --> Execute
    Execute --> Result[FlowRunResult]
    Result --> Trace[ExecutionTrace]
    Result --> Records[artifacts, evidence, reasoning, verification]
    Trace --> Store[DuckDB execution store]
    Records --> Store
```

## Flow Manifest

`FlowManifest` is an immutable declaration of execution authority. It records:

- specification, flow, tenant, and lifecycle state;
- determinism level, replay mode, and acceptable replay variance;
- entropy budget and declared non-deterministic intent;
- replay envelope and dataset descriptor;
- agent and dependency inventory; and
- retrieval contracts and verification gates.

Construction establishes the structure, not complete semantic validity. The
flow contract validates cross-field rules before planning. A caller must not
treat a successfully constructed dataclass as an executable authorization.

## Execution Configuration

`ExecutionConfig` selects plan, dry-run, live, observer, or unsafe behavior
through `RunMode` and binds the execution dependencies: verification policy,
non-determinism policy, artifact and execution stores, budget, observers,
parent-child flow identity, resume identity, and strict-determinism posture.
Replay is a separate workflow over a retained run and read store.

`for_manifest()` aligns the effective determinism level with the manifest while
retaining these dependencies. Executable modes require explicit authority and
storage; plan mode returns a resolved plan without a trace or run ID.

## Policy Records

`NonDeterminismPolicy` bounds allowed entropy and intent sources, minimum and
maximum magnitude, variance class, and justification requirements. An intent
outside those bounds is a contract violation, not a warning.

`VerificationPolicy` binds the verification level, failure behavior,
randomness tolerance, arbitration policy, required evidence, rule-cost limit,
rules, and the rule IDs that halt or escalate execution. Verification results
state what each engine observed; arbitration records the policy decision across
those observations.

## Run Result

`FlowRunResult` returns the resolved plan, finalized trace, artifacts, retrieved
evidence, reasoning bundles, verification results, arbitrations, and persisted
run ID. Its collections are distinct because they carry different authority:

- an `Artifact` records immutable provenance and content identity;
- `RetrievedEvidence` binds evidence to retrieval and content identity;
- a reasoning bundle links steps and claims to evidence; and
- verification records show checks and the resulting governed decision.

## HTTP Boundary

The v1 request models reject unknown fields and require explicit manifest,
input, dataset, policy, mode, and replay identity. `FailureEnvelope` classifies
contract failures separately from successful flow responses. The execution
endpoints are currently unimplemented, however, so these schemas describe a
versioned boundary—not a promise that HTTP execution is operational.

Changes to tenant or flow identity, policy meaning, plan hashing, event order,
entropy accounting, replay acceptability, or failure classification are
compatibility-sensitive. See [Artifact Contracts](artifact-contracts.md) for
the persisted authority record.
