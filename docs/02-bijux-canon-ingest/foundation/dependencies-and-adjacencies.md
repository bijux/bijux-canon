---
title: Dependencies and Adjacencies
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-04-04
---

# Dependencies and Adjacencies

Dependencies and adjacencies explain what `bijux-canon-ingest` can do by itself and
what it deliberately leans on. They are part of the package story, not just
implementation trivia, because they show where local authority ends.

This page helps a reviewer see both kinds of dependency pressure: library
dependencies that shape the implementation, and neighboring packages that shape
the system boundary.

Read the foundation pages as the durable package description for `bijux-canon-ingest`. If the package still feels blurry after this section, the boundary story is not clear enough yet.

## Visual Summary

```mermaid
flowchart LR
    deps["Library pressure<br/>pydantic<br/>msgpack<br/>numpy"]
    package["bijux-canon-ingest<br/>package boundary"]
    adj1["Upstream or downstream<br/>feeds prepared outputs toward index and reason"]
    adj2["Governance seam<br/>stays under runtime governance"]
    deps --> package
    package --> adj1
    package --> adj2
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    classDef action fill:var(--bijux-mermaid-action-fill),stroke:var(--bijux-mermaid-action-stroke),color:var(--bijux-mermaid-action-text);
    class deps anchor;
    class package page;
    class adj1 positive;
    class adj2 caution;
```

## Direct Dependency Themes

- pydantic
- msgpack
- numpy
- fastapi
- uvicorn
- PyYAML

## Adjacent Package Relationships

- feeds prepared material toward bijux-canon-index and bijux-canon-reason
- stays under runtime governance instead of defining replay authority itself

## Concrete Anchors

- `packages/bijux-canon-ingest` as the package root
- `packages/bijux-canon-ingest/src/bijux_canon_ingest` as the import boundary
- `packages/bijux-canon-ingest/tests` as the package proof surface

## Open This Page When

- you need the package idea before the implementation detail
- you are deciding whether work belongs here or in a neighboring package
- you want the shortest honest explanation of what this package is for

## Decision Rule

Use `Dependencies and Adjacencies` to decide whether a change makes `bijux-canon-ingest` easier or harder to defend as one distinct role in the overall system. If the work makes the package broader without making its role clearer, stop and re-check the boundary before treating the change as a local improvement.

## What You Can Resolve Here

- what problem `bijux-canon-ingest` owns on purpose
- where the package boundary stops, even when nearby code looks tempting
- which neighboring package seams deserve comparison before the boundary is changed

## Review Focus

- compare the stated boundary with the modules, artifacts, and tests that uphold it
- check that out-of-scope behavior is not quietly re-entering through convenience paths
- confirm that the package story still matches the real repository layout and neighboring package docs

## Limits

This page shows the intended boundary of `bijux-canon-ingest`, but it cannot prove that boundary by itself. The real proof still lives in the code, tests, and neighboring package seams that either support or contradict the story told here.

## Read Next

- open architecture when the question becomes structural rather than boundary-oriented
- open interfaces when the question becomes contract-facing
- open quality when the question becomes proof or review sufficiency

