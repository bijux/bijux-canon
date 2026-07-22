---
title: Quality
audience: mixed
type: index
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-07-21
---

# Quality

Runtime quality is demonstrated by correct refusal as much as successful
execution. Invalid manifests, undeclared entropy, incomplete verification,
mutable traces, corrupt stores, changed policy, and unacceptable replay must
remain distinguishable outcomes.

## Evidence chain

```mermaid
flowchart LR
    contracts["authority contracts"]
    planning["resolution + plan identity"]
    execution["mode + causal execution"]
    verification["rules + arbitration"]
    persistence["checkpoints + DuckDB"]
    replay["envelope + semantic diff"]
    recovery["crash + hostile-state refusal"]

    contracts --> planning --> execution --> verification --> persistence --> replay --> recovery
```

## Claims and proof

| Trust claim | Required evidence | Important limit |
| --- | --- | --- |
| manifests resolve to stable authority | contract/model tests, dependency resolution, golden plan | dataclass construction alone is not semantic validation |
| each mode preserves its declared guarantees | preparation, strategy, strictness, and matching e2e tests | dry run cannot predict live external effects |
| causal traces cannot escape mutable | event-index, authority, finalization, immutability, snapshot tests | observed mode cannot capture omitted host events |
| nondeterminism is declared and bounded | intent, entropy budget/use, strict guard, canary, replay tests | seeds cannot control unrecorded external variance |
| verification affects acceptance honestly | rule, contradiction, content, arbitration, failure tests | passing registered rules is not factual truth |
| stored runs are resumable and typed | migrations, persistence, round trip, partial failure, crash recovery | DuckDB does not coordinate external side effects |
| replay applies original authority | envelope, exact equivalence, policy, dataset, environment, fuzz tests | state never retained cannot be compared or recovered |
| hostile state is refused | adversarial store, corrupt artifact, mismatch, and compatibility tests | host still owns backup, isolation, and authentication |

## Replay evidence

A replay test asserts both verdict and reason. Envelope hashes detect input
drift; exact-equivalence tests compare governed outputs; trace diff identifies
the earliest changed step; dataset, environment, and policy tests require
refusal when pinned authority changes; cross-process tests prove replay does
not depend on memory; fuzz tests demand stable classification.

Completing without exception is not replay proof. It can conceal a downgrade
from exact equality to tolerated divergence or non-certifiability.

## Recovery evidence

Crash and partial-failure tests reopen incremental state, reconstruct event and
entropy indices, and continue after the last checkpoint. Hostile-store tests
require refusal when write protocols are violated. Long-horizon cases ensure
artifact, evidence, claim, tool, and entropy correlations remain intact across
many steps. External integrations still require their own idempotency or
compensation contract.

## Evidence routes

| Need | Guide |
| --- | --- |
| Understand authority-oriented test layers | [Test strategy](test-strategy.md) |
| Review manifest, mode, trace, entropy, and persistence laws | [Invariants](invariants.md) |
| Select proof for a concrete change | [Change validation](change-validation.md) |
| Apply consistent authority review | [Review checklist](review-checklist.md) |
| Decide whether a governed change is complete | [Definition of done](definition-of-done.md) |
| Govern DuckDB and lower-layer integrations | [Dependency governance](dependency-governance.md) |
| Understand execution, replay, verification, persistence, and hosting limits | [Known limitations](known-limitations.md) |
| Inspect unresolved authority and operational risk | [Risk register](risk-register.md) |
| Interpret execution, acceptance, persistence, and replay independently | [Interpreting runtime evidence](evidence-interpretation.md) |

Add regressions where refusal belongs: contract, planner, executor, verifier,
trace, or store. Add end-to-end proof when invalid authority could look like a
credible result, and replay proof whenever retained identity changes.
