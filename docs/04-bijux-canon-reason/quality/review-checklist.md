---
title: Claim and Evidence Review
audience: mixed
type: how-to
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-07-22
---

# Claim and Evidence Review

Review reconstructs the path from a problem specification to every finalized
claim. Begin with the claimed guarantee, then follow its identifiers and bytes
backward through the retained bundle.

```mermaid
flowchart TD
    claim[Final claim or refusal]
    supports[Support edges]
    evidence[Retained evidence bytes]
    events[Claim and tool events]
    plan[Plan and specification]

    claim --> supports --> evidence --> events --> plan
```

## Reverse one validated claim

Use a validated derived claim because it crosses the most boundaries. Follow
it backward without consulting unretained provider context:

```mermaid
sequenceDiagram
    participant Reviewer
    participant Claim
    participant Verification
    participant Support
    participant Evidence
    participant Trace
    participant Plan

    Reviewer->>Claim: inspect kind, status, identity
    Claim->>Verification: locate findings that permit status
    Claim->>Support: enumerate every support edge
    Support->>Evidence: resolve path, span, and digest
    Evidence->>Trace: locate registration and retrieval event
    Trace->>Plan: identify authorized node and dependencies
```

The audit fails if any arrow depends on a display label, mutable external path,
or prose reconstruction. Claim and evidence identities must resolve within the
manifested run, and the report must explain why the final status follows from
its applicable findings.

## Challenge support and bundle custody

| Mutation | Expected detection |
| --- | --- |
| change one retained evidence byte inside a support span | snippet digest or evidence identity failure |
| keep bytes but move the span outside its registered bounds | support-span validation failure |
| remove an intermediate derived claim | support-graph or provenance failure |
| replace a recorded tool result with a live call during replay | frozen-replay or provenance guard failure |
| omit one applicable verifier result | report completeness failure, not implicit success |
| combine a plan from one run with a trace from another | checksum, identity, topology, or manifest failure |
| delete a core run file but leave `manifest.json` | incomplete bundle refusal |
| change corpus or index identity while preserving answer text | structured replay/provenance difference |

Each negative fixture should reach the invariant it is designed to test. A
test that fails earlier because its JSON is malformed does not demonstrate
that support, provenance, or bundle-integrity checks work.

## Structure and execution

- Are plan identifiers unique, dependencies present, and the graph acyclic?
- Do trace indices increase monotonically and every started step finish?
- Does every tool return reference one known call, with failure behavior
  retained rather than omitted?
- Are runtime descriptor, preset, seed, schema, and canonicalization identity
  present wherever reproducibility is claimed?

## Evidence and claims

- Does every support reference resolve to a governed path within the run root?
- Are byte spans valid and snippet hashes recomputed against retained content?
- Can a derived claim be traced through intermediate supports without a gap?
- Is insufficiency explicit when the available evidence cannot meet the
  requested constraint?

## Verification and bundle custody

- Does the report include every applicable registered check and its details?
- Do negative fixtures fail at the intended invariant rather than an earlier,
  unrelated parser?
- Do manifest digests, run metadata, trace checksum, and core files describe
  the same execution?
- Is an incomplete directory impossible to consume as a completed bundle?

## Replay and behavioral evidence

- Does replay use recorded tool results and pinned retrieval artifacts only?
- Are corpus, index, plan, or provenance changes rejected or exposed in the
  structured diff?
- Does an answer-quality claim identify the corpus, cases, constraints,
  expected refusal behavior, and metrics?
- Are truth, authority, freshness, and consequential fitness left to explicit
  source governance and domain review?

Conclude with [evidence release acceptance](definition-of-done.md) and compare
the claim with [known limitations](known-limitations.md).
