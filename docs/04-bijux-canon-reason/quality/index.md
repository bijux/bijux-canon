---
title: Quality
audience: mixed
type: index
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-07-21
---

# Quality

Reason quality has two independent dimensions: integrity of the reasoning
record and behavior of the reference workflow. A bundle can be internally
valid yet scientifically unhelpful; a plausible answer can be invalid because
its evidence, support, or trace was corrupted.

## Evidence chain

```mermaid
flowchart LR
    model["models + canonical identity"]
    plan["DAG and execution order"]
    support["evidence + exact spans"]
    checks["registered verification"]
    artifact["fingerprint + manifest"]
    replay["frozen replay + diff"]
    evaluation["declared corpus + cases"]

    model --> plan --> support --> checks --> artifact --> replay --> evaluation
```

## Integrity claims

| Trust claim | Evidence | Failure that must remain visible |
| --- | --- | --- |
| identities are stable | canonical serialization and cross-platform fingerprint tests | content change hidden behind reused identity |
| plans are executable DAGs | planner and topology tests | cycle, missing dependency, duplicate node |
| trace history is coherent | event ordering, lifecycle, tool-call/return linkage tests | orphan return, unfinished action, unknown step |
| claims have exact support | span, snippet hash, evidence path, derived-grounding tests | nearby citation or changed bytes accepted as support |
| verification is complete | one focused pass/fail test per registered check | parser failure masking the intended invariant |
| run files constrain one another | manifest, fingerprint, checksum, and typed-reader tests | individually plausible but inconsistent files |
| replay uses frozen evidence | replay gate and changed-corpus refusal tests | live retrieval silently replacing the snapshot |

## Behavioral claims

Evaluation cases declare corpus, problem constraints, expected verification
behavior, and acceptable insufficiency. Case and aggregate artifacts expose
verification failures, insufficiency rate, and failure taxonomy. Retrieval or
reasoning changes are assessed against those records, not process exit alone.

The local retrieval benchmark is a regression sentinel tied to its recorded
environment. It is not a service-level objective or evidence that the
reference extractive workflow generalizes beyond its suite.

## Tamper posture

The evidence suite deliberately changes source bytes, support spans, corpus and
index files, plan metadata, tool returns, plan references, and graph topology.
Each mutation must fail at its owning invariant. This precision matters: a
generic parse error is weaker evidence than detecting the actual violated
contract.

## Evidence routes

| Need | Guide |
| --- | --- |
| Understand integrity and behavior test layers | [Test strategy](test-strategy.md) |
| Review structural, evidence, artifact, and replay laws | [Invariants](invariants.md) |
| Select proof for a change | [Change validation](change-validation.md) |
| Apply review questions consistently | [Review checklist](review-checklist.md) |
| Decide whether evidence is release-ready | [Definition of done](definition-of-done.md) |
| Review runtime and optional dependencies | [Dependency governance](dependency-governance.md) |
| Understand epistemic, replay, interface, and resource limits | [Known limitations](known-limitations.md) |
| Inspect unresolved failure modes | [Risk register](risk-register.md) |
| Keep public claims within demonstrated evidence | [Documentation standards](documentation-standards.md) |

Add regressions at the model, planner, executor, retriever, verifier, or replay
owner first. Add a manifested-run test when invalid behavior could otherwise
survive as convincing evidence, and an evaluation case when semantic behavior
rather than artifact validity changed.
