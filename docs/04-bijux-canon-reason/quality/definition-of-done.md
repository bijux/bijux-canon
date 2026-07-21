---
title: Evidence Release Acceptance
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-07-21
---

# Evidence Release Acceptance

A reasoning change is releasable when its claims, support, trace, verification,
bundle, and replay record constrain one another. Fluent output, a passing
process, or a stable fingerprint cannot substitute for that chain.

```mermaid
flowchart LR
    spec[Problem specification]
    plan[Content-addressed plan]
    trace[Ordered trace]
    support[Evidence and support spans]
    verify[Verification report]
    bundle[Manifested bundle]
    replay[Frozen replay]

    spec --> plan --> trace --> support --> verify --> bundle --> replay
```

## Acceptance record

| Changed surface | Required evidence | Release-blocking result |
| --- | --- | --- |
| model, identifier, or canonicalization | validation, stable-ID, cross-platform serialization, and changed-content comparison | different content reuses an identity |
| plan topology | deterministic DAG fixtures, cycle and missing-dependency refusal | an invalid graph reaches execution |
| tool or lifecycle event | call/return linkage, event order, failure, and unfinished-step cases | an orphan or incomplete action is finalized |
| evidence registration | governed path, retained bytes, content digest, span bounds, and chunk identity | support resolves outside the bundle or against changed bytes |
| claim construction | support edges, status, confidence, type, and insufficiency cases | a derived unsupported claim is finalized |
| verifier | one positive and targeted negative case for every affected check | corruption passes or fails only through an unrelated parse error |
| manifested run | core-file inventory, digests, runtime identity, checksum, and incomplete bundle refusal | individually plausible files describe different runs |
| replay | original checksum, frozen tool results, pinned retrieval artifacts, fingerprint, and structured diff | replay consults live retrieval or accepts provenance drift |
| behavioral claim | named corpus, cases, constraints, insufficiency policy, and metric artifacts | artifact validity is presented as scientific usefulness |

## Custody and interpretation

Retain the specification, plan, runtime descriptor, trace, evidence bytes,
claims, verification reports, run metadata, manifest, and replay output as one
review unit. A trace fingerprint establishes identity of the trace file; it
does not establish source authority, entailment, completeness, or truth.

An `insufficient_evidence` result is acceptable when the case and policy allow
refusal. Hiding that refusal behind an empty or confident answer is not.

Use [change validation](change-validation.md) to route focused evidence and
[known limitations](known-limitations.md) to bound the resulting release claim.
