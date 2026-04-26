---
title: Change Principles
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-04-04
---

# Change Principles

Changes in `bijux-canon-reason` should leave the package easier to explain, not
harder. A good change makes ownership clearer, contract language more honest,
and the proof story easier to follow.

These principles are not slogans. They are the filter for deciding whether a
local improvement is worth the long-term cost it creates for the rest of the
system.

Treat the foundation pages for `bijux-canon-reason` as the package's durable self-description. If the package still feels blurry after this section, the boundary story is not clear enough yet.

## Visual Summary

```mermaid
flowchart LR
    page["Change Principles<br/>clarifies: own the right work | name the boundary | compare neighbors"]
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    classDef action fill:var(--bijux-mermaid-action-fill),stroke:var(--bijux-mermaid-action-stroke),color:var(--bijux-mermaid-action-text);
    own1["execution of reasoning steps and local tool dispatch"]
    own1 --> page
    own2["verification and provenance checks that belong to reasoning itself"]
    own2 --> page
    own3["reasoning plans, claims, and evidence-aware reasoning models"]
    own3 --> page
    limit1["repository tooling and release automation"]
    page -.keeps outside.-> limit1
    limit2["runtime persistence and replay authority"]
    page -.keeps outside.-> limit2
    limit3["ingest and index engines"]
    page -.keeps outside.-> limit3
    anchor1["packages/bijux-canon-reason/src/bijux_canon_reason"]
    page --> anchor1
    anchor2["packages/bijux-canon-reason/tests"]
    page --> anchor2
    anchor3["packages/bijux-canon-reason"]
    page --> anchor3
    class page page;
    class own1,own2,own3 positive;
    class limit1,limit2,limit3 caution;
    class anchor1,anchor2,anchor3 anchor;
```

## Principles

- prefer moving behavior toward the owning package instead of letting boundary overlap grow
- update docs and tests in the same change series that changes package behavior
- keep names stable and descriptive enough to survive years of maintenance

## Concrete Anchors

- `packages/bijux-canon-reason` as the package root
- `packages/bijux-canon-reason/src/bijux_canon_reason` as the import boundary
- `packages/bijux-canon-reason/tests` as the package proof surface

## Use This Page When

- you need the package idea before the implementation detail
- you are deciding whether work belongs here or in a neighboring package
- you want the shortest honest explanation of what this package is for

## Decision Rule

Use `Change Principles` to decide whether a change makes `bijux-canon-reason` easier or harder to defend as one distinct role in the overall system. If the work makes the package broader without making its role clearer, stop and re-check the boundary before treating the change as a local improvement.

## What This Page Answers

- what problem `bijux-canon-reason` is supposed to own on purpose
- where the package boundary stops, even when nearby code looks tempting
- which neighboring package seams deserve comparison before the boundary is changed

## Reviewer Lens

- compare the stated boundary with the modules, artifacts, and tests that are supposed to uphold it
- check that out-of-scope behavior is not quietly re-entering through convenience paths
- confirm that the package story still matches the real repository layout and neighboring package docs

## Honesty Boundary

This page can explain the intended boundary of `bijux-canon-reason`, but it cannot prove that boundary by itself. The real proof still lives in the code, tests, and neighboring package seams that either support or contradict the story told here.

## Next Checks

- move to architecture when the question becomes structural rather than boundary-oriented
- move to interfaces when the question becomes contract-facing
- move to quality when the question becomes proof or review sufficiency

## Purpose

This page records the package-specific contribution posture.

## Stability

Update these principles only when the package operating model truly changes.
