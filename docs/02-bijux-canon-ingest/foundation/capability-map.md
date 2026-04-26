---
title: Capability Map
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-04-04
---

# Capability Map

The fastest way to understand `bijux-canon-ingest` is to map capabilities to the
code that carries them. This page helps a reader move from a package claim
to a likely code area without pretending that module names alone are enough.

When this page is healthy, the package feels like a set of deliberate abilities,
not a pile of implementation details.

Read the foundation pages as the durable package description for `bijux-canon-ingest`. If the package still feels blurry after this section, the boundary story is not clear enough yet.

## Visual Summary

```mermaid
flowchart LR
    package["bijux-canon-ingest<br/>capabilities to modules"]
    cap1["document cleaning, normalization, and chunking"]
    mod1["processing<br/>deterministic document transforms"]
    package --> cap1
    cap1 --> mod1
    cap2["ingest-local retrieval and indexing assembly"]
    mod2["retrieval<br/>retrieval-oriented models and assembly"]
    package --> cap2
    cap2 --> mod2
    cap3["package-local CLI and HTTP boundaries"]
    mod3["application<br/>package workflows"]
    package --> cap3
    cap3 --> mod3
    output["Visible output<br/>normalized document trees"]
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

- `src/bijux_canon_ingest/processing` for deterministic document transforms
- `src/bijux_canon_ingest/retrieval` for retrieval-oriented models and assembly
- `src/bijux_canon_ingest/application` for package workflows
- `src/bijux_canon_ingest/infra` for local adapters and infrastructure helpers
- `src/bijux_canon_ingest/interfaces` for CLI and HTTP boundaries
- `src/bijux_canon_ingest/safeguards` for protective rules for ingest behavior

## Produced Artifacts

- normalized document trees
- chunk collections and retrieval-ready records
- diagnostic output produced during ingest workflows

## Concrete Anchors

- `packages/bijux-canon-ingest` as the package root
- `packages/bijux-canon-ingest/src/bijux_canon_ingest` as the import boundary
- `packages/bijux-canon-ingest/tests` as the package proof surface

## Use This Page When

- you need the package idea before the implementation detail
- you are deciding whether work belongs here or in a neighboring package
- you want the shortest honest explanation of what this package is for

## Decision Rule

Use `Capability Map` to decide whether a change makes `bijux-canon-ingest` easier or harder to defend as one distinct role in the overall system. If the work makes the package broader without making its role clearer, stop and re-check the boundary before treating the change as a local improvement.

## What This Page Answers

- what problem `bijux-canon-ingest` owns on purpose
- where the package boundary stops, even when nearby code looks tempting
- which neighboring package seams deserve comparison before the boundary is changed

## Reviewer Lens

- compare the stated boundary with the modules, artifacts, and tests that uphold it
- check that out-of-scope behavior is not quietly re-entering through convenience paths
- confirm that the package story still matches the real repository layout and neighboring package docs

## Honesty Boundary

This page shows the intended boundary of `bijux-canon-ingest`, but it cannot prove that boundary by itself. The real proof still lives in the code, tests, and neighboring package seams that either support or contradict the story told here.

## Next Checks

- open architecture when the question becomes structural rather than boundary-oriented
- open interfaces when the question becomes contract-facing
- open quality when the question becomes proof or review sufficiency

## Purpose

This page helps a reader quickly map package claims to code areas.

## Stability

Keep it aligned with the real package modules and generated outputs.
