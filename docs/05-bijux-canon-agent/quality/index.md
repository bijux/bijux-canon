---
title: Quality
audience: mixed
type: index
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-07-21
---

# Quality

Agent quality is the coherence of the orchestration record, not the fluency of
its final artifact. Contracts, lifecycle, convergence, termination, trace, and
public adapters each need focused proof before a run can be called auditable.

## Evidence chain

```mermaid
flowchart LR
    contracts["strict role contracts"]
    lifecycle["owned transitions"]
    roles["bounded role behavior"]
    outcome["merge + convergence + termination"]
    trace["schema + ordering + replayability"]
    boundary["CLI / HTTP / artifacts"]
    limits["model and hosting limits"]

    contracts --> lifecycle --> roles --> outcome --> trace --> boundary --> limits
```

## Claims and proof

| Trust claim | Required evidence | Important limit |
| --- | --- | --- |
| role calls have stable contracts | strict input/output/error and metadata tests | schema validity does not establish correctness |
| lifecycle authority is centralized | transition, kernel-order, architecture, and passive-role invariants | custom graphs need equivalent declared evidence |
| role behavior remains bounded | focused role tests and no-lifecycle-override checks | provider behavior remains external |
| sharded work has honest outcome | shard merge, failure assembly, final validation, telemetry tests | one success must not conceal failed inputs |
| convergence is reproducible | strategy, snapshot, window hash, oscillation, termination tests | stable agreement can still be wrong |
| traces are reviewable | mandatory fields, ordering, completeness, schema version, serialization tests | missing host/provider events cannot be reconstructed |
| replay designation is honest | frozen time, deterministic hash, zero-temperature, negative replay tests | replay does not recreate historical model serving |
| public surfaces agree | CLI/HTTP parity, OpenAPI, artifact, and golden example tests | HTTP v1 intentionally has a narrower fixed pipeline |

## Snapshot and live-test discipline

Snapshots protect architecture contracts, version defaults, kernel behavior,
trace schema, and representative artifacts. Review their semantic changes;
regenerating expected output without explaining a field, transition, or
default change erases compatibility evidence.

Live provider tests answer only whether an adapter can contact the provider
and record its response metadata. They are opt-in evidence and do not replace
deterministic orchestration tests or representative model evaluation.

## Evidence routes

| Need | Guide |
| --- | --- |
| Understand contracts, lifecycle, trace, and boundary test layers | [Test strategy](test-strategy.md) |
| Review lifecycle, contract, trace, and convergence laws | [Invariants](invariants.md) |
| Select proof for a concrete change | [Change validation](change-validation.md) |
| Apply consistent review questions | [Review checklist](review-checklist.md) |
| Decide whether orchestration evidence is complete | [Definition of done](definition-of-done.md) |
| Govern model providers and optional integrations | [Dependency governance](dependency-governance.md) |
| Understand model, convergence, replay, credential, and hosting limits | [Known limitations](known-limitations.md) |
| Inspect unresolved workflow and operational risk | [Risk register](risk-register.md) |
| Keep public capability claims within evidence | [Documentation standards](documentation-standards.md) |

Reproduce defects at the narrowest contract, role, lifecycle, convergence,
trace, or interface owner. Add pipeline-level proof when terminal status or
artifact completeness changes, and parity proof when adapters could diverge.
