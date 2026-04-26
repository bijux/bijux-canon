---
title: Change Principles
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-04-04
---

# Change Principles

Changes in `bijux-canon-agent` should leave the package easier to explain, not
harder. A good change makes ownership clearer, contract language more honest,
and the proof story easier to follow.

These principles are not slogans. They are the filter for deciding whether a
local improvement is worth the long-term cost it creates for the rest of the
system.

The foundation pages are the durable package description. If the package still feels blurry after this section, the boundary story is not clear enough yet.

## Visual Summary

```mermaid
flowchart TB
    change["Change proposal"]
    boundary["Keep ownership inside<br/>bijux-canon-agent"]
    explain["Update docs with code"]
    prove["Update tests with behavior"]
    stable["Keep names durable and clear"]
    change --> boundary
    boundary --> explain
    boundary --> prove
    prove --> stable
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    classDef action fill:var(--bijux-mermaid-action-fill),stroke:var(--bijux-mermaid-action-stroke),color:var(--bijux-mermaid-action-text);
    class change page;
    class boundary positive;
    class explain action;
    class prove anchor;
    class stable caution;
```

## Principles

- prefer moving behavior toward the owning package instead of letting boundary overlap grow
- update docs and tests in the same change series that changes package behavior
- keep names stable and descriptive enough to survive years of maintenance

## Concrete Anchors

- `packages/bijux-canon-agent` as the package root
- `packages/bijux-canon-agent/src/bijux_canon_agent` as the import boundary
- `packages/bijux-canon-agent/tests` as the package proof surface

## Open This Page When

- you need the package idea before the implementation detail
- you are deciding whether work belongs here or in a neighboring package
- you want the shortest honest explanation of what this package is for

## Decision Rule

Use `Change Principles` to decide whether a change makes `bijux-canon-agent` easier or harder to defend as one distinct role in the overall system. If the work makes the package broader without making its role clearer, stop and re-check the boundary before treating the change as a local improvement.

## What You Can Resolve Here

- what problem `bijux-canon-agent` owns on purpose
- where the package boundary stops, even when nearby code looks tempting
- which neighboring package seams deserve comparison before the boundary is changed

## Review Focus

- compare the stated boundary with the modules, artifacts, and tests that uphold it
- check that out-of-scope behavior is not quietly re-entering through convenience paths
- confirm that the package story still matches the real repository layout and neighboring package docs

## Limits

This page can explain the intended boundary of `bijux-canon-agent`, but it cannot prove that boundary by itself. The real proof still lives in the code, tests, and neighboring package seams that either support or contradict the story told here.

## Read Next

- open architecture when the question becomes structural rather than boundary-oriented
- open interfaces when the question becomes contract-facing
- open quality when the question becomes proof or review sufficiency

