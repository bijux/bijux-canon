---
title: Quality
audience: mixed
type: index
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-26
---

# Quality

Use this section when the real question is whether index behavior can be
trusted: which tests prove retrieval and replay behavior, which risks remain
visible, and what "done" should mean before reasoning or runtime depend on the
result.

These pages should keep reviewers honest about the cost of being wrong in the
retrieval layer. If index behavior drifts quietly, downstream packages can still
look healthy while using stale, incomplete, or unreplayable retrieval results.

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

- open [Test Strategy](test-strategy.md) for the broad proof story behind
  retrieval behavior
- open [Invariants](invariants.md) when the key question is what must not drift
  across index state, provenance, or replay
- open [Change Validation](change-validation.md) when you need the minimum
  evidence for a safe retrieval change
- open [Risk Register](risk-register.md) when backend limitations or tradeoffs
  matter more than pass/fail status

## Pages In This Section

- [Test Strategy](test-strategy.md)
- [Invariants](invariants.md)
- [Review Checklist](review-checklist.md)
- [Documentation Standards](documentation-standards.md)
- [Definition of Done](definition-of-done.md)
- [Dependency Governance](dependency-governance.md)
- [Change Validation](change-validation.md)
- [Known Limitations](known-limitations.md)
- [Risk Register](risk-register.md)

## Use This Section When

- you need evidence that retrieval behavior is stable enough for downstream use
- a change touches indexing, replay, provenance, or backend behavior that can
  drift quietly
- you are reviewing whether green checks are actually sufficient for the
  contract being changed

## Do Not Use This Section When

- the real question is which command, schema, or artifact surface exists
- you need the package boundary or structural flow before you can judge proof
- the issue is about how to run the package rather than how to trust it

## Read Across The Package

- open [Foundation](../foundation/index.md) when uncertainty about ownership is
  masquerading as a quality issue
- open [Architecture](../architecture/index.md) when missing proof points to
  structural drift
- open [Interfaces](../interfaces/index.md) when trust depends on a specific
  retrieval contract
- open [Operations](../operations/index.md) when the needed evidence is really a
  repeatable replay or recovery workflow

## Concrete Anchors

- `tests/unit` for API, application, contracts, domain, infra, and tooling
- `tests/e2e` for CLI workflows, API smoke, determinism gates, and provenance
  gates
- `README.md`

## Reader Takeaway

Use `Quality` to ask a stricter question than “did the suite pass?” In index,
the real bar is whether retrieval behavior remains replayable, provenance-aware,
and honest about backend limits before downstream packages treat it as stable
ground.

## Purpose

This page introduces the quality handbook for `bijux-canon-index` and routes
readers to the proof, invariants, review, validation, and risk pages that show
how trust is earned.
