---
title: Quality
audience: mixed
type: index
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-26
---

# Quality

Open this section when you need to know whether index behavior can be trusted:
which tests prove retrieval and replay behavior, which risks remain visible,
and what "done" should mean before reasoning or runtime depend on the result.

These pages keep reviewers honest about the cost of being wrong in the
retrieval layer. If index behavior drifts quietly, downstream packages can
still look healthy while using stale, incomplete, or unreplayable retrieval
results.

## Visual Summary

```mermaid
flowchart LR
    ingest["prepared ingest input"]
    retrieval["retrieval proof<br/>query and result behavior"]
    replay["replay proof<br/>state can be rebuilt and checked"]
    review["review pressure<br/>what a safe retrieval change must show"]
    risks["visible limitations<br/>backend tradeoffs and blind spots"]
    downstream["downstream trust<br/>reasoning and runtime depend on this"]
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    classDef action fill:var(--bijux-mermaid-action-fill),stroke:var(--bijux-mermaid-action-stroke),color:var(--bijux-mermaid-action-text);
    class ingest,page downstream;
    class retrieval,replay positive;
    class review action;
    class risks caution;
    ingest --> retrieval --> replay --> downstream
    retrieval --> review
    replay --> review
    review --> risks
```

## Start Here

- use [Test Strategy](https://bijux.io/bijux-canon/03-bijux-canon-index/quality/test-strategy/) for the broad proof story behind
  retrieval behavior
- use [Invariants](https://bijux.io/bijux-canon/03-bijux-canon-index/quality/invariants/) when the key question is what must not drift
  across index state, provenance, or replay
- use [Change Validation](https://bijux.io/bijux-canon/03-bijux-canon-index/quality/change-validation/) when you need the minimum
  evidence for a safe retrieval change
- use [Risk Register](https://bijux.io/bijux-canon/03-bijux-canon-index/quality/risk-register/) when backend limitations or tradeoffs
  matter more than pass/fail status

## Pages In Quality

- [Test Strategy](https://bijux.io/bijux-canon/03-bijux-canon-index/quality/test-strategy/)
- [Invariants](https://bijux.io/bijux-canon/03-bijux-canon-index/quality/invariants/)
- [Review Checklist](https://bijux.io/bijux-canon/03-bijux-canon-index/quality/review-checklist/)
- [Documentation Standards](https://bijux.io/bijux-canon/03-bijux-canon-index/quality/documentation-standards/)
- [Definition of Done](https://bijux.io/bijux-canon/03-bijux-canon-index/quality/definition-of-done/)
- [Dependency Governance](https://bijux.io/bijux-canon/03-bijux-canon-index/quality/dependency-governance/)
- [Change Validation](https://bijux.io/bijux-canon/03-bijux-canon-index/quality/change-validation/)
- [Known Limitations](https://bijux.io/bijux-canon/03-bijux-canon-index/quality/known-limitations/)
- [Risk Register](https://bijux.io/bijux-canon/03-bijux-canon-index/quality/risk-register/)

## Use Quality When

- you need evidence that retrieval behavior is stable enough for downstream use
- a change touches indexing, replay, provenance, or backend behavior that can
  drift quietly
- you are reviewing whether green checks are actually sufficient for the
  contract being changed

## Open Another Section When

- the real question is which command, schema, or artifact surface exists
- you need the package boundary or structural flow before you can judge proof
- the issue is about how to run the package rather than how to trust it

## Read Across The Package

- use [Foundation](https://bijux.io/bijux-canon/03-bijux-canon-index/foundation/) when uncertainty about ownership is
  masquerading as a quality issue
- use [Architecture](https://bijux.io/bijux-canon/03-bijux-canon-index/architecture/) when missing proof points to
  structural drift
- use [Interfaces](https://bijux.io/bijux-canon/03-bijux-canon-index/interfaces/) when trust depends on a specific
  retrieval contract
- use [Operations](https://bijux.io/bijux-canon/03-bijux-canon-index/operations/) when the needed evidence is really a
  repeatable replay or recovery workflow

## Concrete Anchors

- `tests/unit` for API, application, contracts, domain, infra, and tooling
- `tests/e2e` for CLI workflows, API smoke, determinism gates, and provenance
  gates
- `README.md`

## Why Use Quality

Open `Quality` to ask a stricter question than “did the suite pass?” In index,
the real bar is whether retrieval behavior remains replayable, provenance-aware,
and honest about backend limits before downstream packages treat it as stable
ground.

## What You Get

Open this page when you need the proof, invariants, review, validation, and
risk route through `bijux-canon-index` before you inspect a specific trust
surface.
