---
title: Capability Map
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-04
---

# Capability Map

The fastest way to understand `bijux-canon-index` is to map capabilities to the
code that carries them. This page helps a reader move from a package claim
to a likely code area without pretending that module names alone are enough.

When this page is healthy, the package feels like a set of deliberate abilities,
not a pile of implementation details.

Read the foundation pages as the durable package description for `bijux-canon-index`. If the package still feels blurry after this section, the boundary story is not clear enough yet.

## Visual Summary

```mermaid
flowchart LR
    package["bijux-canon-index<br/>capabilities to modules"]
    cap1["vector execution semantics and backend orchestration"]
    mod1["domain<br/>execution, provenance, and request"]
    package --> cap1
    cap1 --> mod1
    cap2["provenance-aware result artifacts and replay-oriented comparison"]
    mod2["application<br/>workflow coordination"]
    package --> cap2
    cap2 --> mod2
    cap3["plugin-backed vector store, embedding, and runner"]
    mod3["infra<br/>backends, adapters, and runtime"]
    package --> cap3
    cap3 --> mod3
    output["Visible output<br/>vector execution result collections"]
    mod3 --> output
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    classDef action fill:var(--bijux-mermaid-action-fill),stroke:var(--bijux-mermaid-action-stroke),color:var(--bijux-mermaid-action-text);
    class package page;
    class cap1,cap2,cap3 positive;
    class mod1,mod2,mod3 anchor;
    class output action;
```

## Capability Map

- `src/bijux_canon_index/domain` for execution, provenance, and request semantics
- `src/bijux_canon_index/application` for workflow coordination
- `src/bijux_canon_index/infra` for backends, adapters, and runtime environment helpers
- `src/bijux_canon_index/interfaces` for CLI and operator-facing edges
- `src/bijux_canon_index/api` for HTTP application surfaces
- `src/bijux_canon_index/contracts` for stable contract definitions

## Produced Artifacts

- vector execution result collections
- provenance and replay comparison reports
- backend-specific metadata and audit output

## Concrete Anchors

- `packages/bijux-canon-index` as the package root
- `packages/bijux-canon-index/src/bijux_canon_index` as the import boundary
- `packages/bijux-canon-index/tests` as the package proof surface

## Open This Page When

- you need the package idea before the implementation detail
- you are deciding whether work belongs here or in a neighboring package
- you want the shortest honest explanation of what this package is for

## Decision Rule

Use `Capability Map` to decide whether a change makes `bijux-canon-index` easier or harder to defend as one distinct role in the overall system. If the work makes the package broader without making its role clearer, stop and re-check the boundary before treating the change as a local improvement.

## What You Can Resolve Here

- what problem `bijux-canon-index` owns on purpose
- where the package boundary stops, even when nearby code looks tempting
- which neighboring package seams deserve comparison before the boundary is changed

## Review Focus

- compare the stated boundary with the modules, artifacts, and tests that uphold it
- check that out-of-scope behavior is not quietly re-entering through convenience paths
- confirm that the package story still matches the real repository layout and neighboring package docs

## Limits

This page shows the intended boundary of `bijux-canon-index`, but it cannot prove that boundary by itself. The real proof still lives in the code, tests, and neighboring package seams that either support or contradict the story told here.

## Read Next

- open architecture when the question becomes structural rather than boundary-oriented
- open interfaces when the question becomes contract-facing
- open quality when the question becomes proof or review sufficiency

