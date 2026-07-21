---
title: Artifact Contracts
audience: mixed
type: reference
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-07-21
---

# Artifact Contracts

Runtime artifacts are authority records, not arbitrary blobs. Identity,
tenancy, content hashes, parentage, trace order, verification policy, and
replay semantics remain explicit from execution through persistence.

## Flow Result

`FlowRunResult` is the complete in-process handoff:

| Field | Contract |
| --- | --- |
| `resolved_flow` | manifest-derived, plan-hashed execution authority |
| `trace` | finalized execution trace; absent only for plan mode |
| `artifacts` | immutable produced artifact records |
| `evidence` | retrieved evidence with content identity |
| `reasoning_bundles` | claims and their evidence relationship |
| `verification_results` | per-engine rule outcomes |
| `verification_arbitrations` | policy-governed final decisions |
| `run_id` | persisted run identity; absent in plan mode |

## Artifact Record

An `Artifact` carries specification version, artifact and tenant IDs, artifact
type, producer (`agent`, `retrieval`, or `reasoning`), parent artifact IDs,
content hash, and scope. The record is immutable. Payload storage may live
elsewhere; this contract retains the provenance needed to identify it.

Artifact IDs alone are not integrity evidence. Compare content hashes and
parentage, and enforce tenant scope whenever artifacts cross an interface.

## Finalized Trace

An `ExecutionTrace` binds execution to:

- flow, tenant, parent, and child identities;
- flow and dataset state;
- determinism level, replay mode, acceptability, and envelope;
- environment, plan, verification-policy, and resolver fingerprints;
- ordered events and tool invocations;
- recorded entropy use;
- claim IDs, contradiction count, and arbitration decision; and
- exhaustion and certifiability status.

The trace can be accessed only after finalization. Events, tool calls, evidence,
or fields cannot be amended after that boundary without invalidating runtime
authority.

## Verification Evidence

Each verification result names its engine, deterministic or non-deterministic
classification, phase, applied rules, violated rules, checked artifacts,
status, reason, and decision. Arbitration then records the policy fingerprint,
arbitration rule, participating engines and statuses, target artifacts, and
decision.

Keeping engine results separate from arbitration is important: a policy can
escalate or halt on selected rules without rewriting what an engine observed.

## DuckDB Execution Store

The execution store is the durable run boundary. Its governed records include:

- runs, datasets, and normalized plan actions;
- ordered execution events and checkpoints;
- artifact records and artifact-parent edges;
- evidence, claim IDs, and tool invocations;
- entropy budget, sources, intent, and observed use;
- finalized trace metadata and replay policy; and
- schema migrations and the active schema contract hash.

Write and read capabilities are exposed separately. Replay uses the read store;
live and resumed execution use the write store. The schema is migration-owned;
editing tables outside that contract can make a syntactically readable database
semantically unreplayable.

## Replay Acceptability

Replay verdicts are `acceptable`, `acceptable_with_warnings`, `unacceptable`,
or `non_certifiable`. Strict mode rejects any difference. Bounded replay can
accept event, artifact, and evidence differences only when the declared
acceptability permits them; plan, tenant, environment, dataset, policy, or
replay-envelope differences remain blocking. A non-certifiable observed trace
cannot be promoted to acceptable by a permissive diff policy.

See [Execution Model](../architecture/execution-model.md) for the lifecycle that
produces and freezes these records.
