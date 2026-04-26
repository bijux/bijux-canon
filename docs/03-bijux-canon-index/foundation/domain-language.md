---
title: Domain Language
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-04
---

# Domain Language

The language around `bijux-canon-index` should reinforce the real package
boundary. Good names shorten review. Weak names force people to keep asking
whether they are looking at local behavior or at something owned elsewhere.

This page keeps the package vocabulary stable enough that docs, code, commit
messages, and review conversations can describe the same idea without drift.

The foundation pages are the durable package description. If the package still feels blurry after this section, the boundary story is not clear enough yet.

## Visual Summary

```mermaid
flowchart LR
    name["Package name<br/>bijux-canon-index"]
    importroot["Import root<br/>bijux_canon_index"]
    cli["Reader entrypoint<br/>python import surface"]
    artifact["Output nouns<br/>vector execution result collections<br/>provenance and replay comparison reports"]
    name --> importroot
    importroot --> cli
    importroot --> artifact
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    classDef action fill:var(--bijux-mermaid-action-fill),stroke:var(--bijux-mermaid-action-stroke),color:var(--bijux-mermaid-action-text);
    class name page;
    class importroot anchor;
    class cli positive;
    class artifact action;
```

## Package Vocabulary Anchors

- package name: `bijux-canon-index`
- Python import root: `bijux_canon_index`
- owning package directory: `packages/bijux-canon-index`
- key outputs: vector execution result collections, provenance and replay comparison reports, backend-specific metadata and audit output

## Concrete Anchors

- `packages/bijux-canon-index` as the package root
- `packages/bijux-canon-index/src/bijux_canon_index` as the import boundary
- `packages/bijux-canon-index/tests` as the package proof surface

## Open This Page When

- you need the package idea before the implementation detail
- you are deciding whether work belongs here or in a neighboring package
- you want the shortest honest explanation of what this package is for

## Decision Rule

Use `Domain Language` to decide whether a change makes `bijux-canon-index` easier or harder to defend as one distinct role in the overall system. If the work makes the package broader without making its role clearer, stop and re-check the boundary before treating the change as a local improvement.

## What You Can Resolve Here

- what problem `bijux-canon-index` owns on purpose
- where the package boundary stops, even when nearby code looks tempting
- which neighboring package seams deserve comparison before the boundary is changed

## Review Focus

- compare the stated boundary with the modules, artifacts, and tests that uphold it
- check that out-of-scope behavior is not quietly re-entering through convenience paths
- confirm that the package story still matches the real repository layout and neighboring package docs

## Limits

Code, tests, and neighboring package seams remain the proof of this boundary.

## Read Next

- open architecture when the question becomes structural rather than boundary-oriented
- open interfaces when the question becomes contract-facing
- open quality when the question becomes proof or review sufficiency

