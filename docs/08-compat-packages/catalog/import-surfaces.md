---
title: Import Surfaces
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-04
---

# Import Surfaces

Compatibility imports exist only so older code can keep resolving package names
during migration.

Preserved imports are a migration aid, not a sign that the legacy name regained
first-class status.

## Visual Summary

```mermaid
flowchart TB
    legacy1["agentic_flows"]
    legacy2["bijux_agent"]
    legacy3["bijux_rag"]
    legacy4["bijux_rar"]
    legacy5["bijux_vex"]
    canon1["bijux_canon_runtime"]
    canon2["bijux_canon_agent"]
    canon3["bijux_canon_ingest"]
    canon4["bijux_canon_reason"]
    canon5["bijux_canon_index"]
    note["Older code keeps importing<br/>the old module name during migration"]
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    classDef action fill:var(--bijux-mermaid-action-fill),stroke:var(--bijux-mermaid-action-stroke),color:var(--bijux-mermaid-action-text);
    legacy1 --> canon1
    legacy2 --> canon2
    legacy3 --> canon3
    legacy4 --> canon4
    legacy5 --> canon5
    note --> legacy1
    note --> legacy2
    note --> legacy3
    note --> legacy4
    note --> legacy5
    class canon1,canon2,canon3,canon4,canon5 positive;
    class legacy1,legacy2,legacy3,legacy4,legacy5 caution;
    class note anchor;
```

## Current Import Roots

- `agentic_flows`
- `bijux_agent`
- `bijux_rag`
- `bijux_rar`
- `bijux_vex`

## Concrete Anchors

- `packages/compat-*` for the preserved legacy packages
- the compatibility package `README.md` files for canonical targets
- the matching canonical package docs for current behavior and new work

## Use This Page When

- you are tracing a legacy package name back to its canonical replacement
- you need migration guidance rather than product implementation detail
- you are deciding whether a compatibility surface still deserves to exist

## Decision Rule

Use this page when the main question is whether a preserved import still serves
a real migration need. If the only reason to keep it is habit rather than an
identified dependent environment, plan migration or retirement instead.

## What This Page Answers

- which legacy import roots are still preserved
- which canonical import roots replace them
- what evidence would justify retiring a compatibility import surface

## Reviewer Lens

- compare legacy names here with the compatibility package metadata and README targets
- check that migration advice still points at current canonical docs
- confirm that compatibility language does not accidentally encourage new work to start here

## Next Checks

- move to the canonical package docs once the current target package is known:
  `https://bijux.io/bijux-canon/02-bijux-canon-ingest/`,
  `https://bijux.io/bijux-canon/03-bijux-canon-index/`,
  `https://bijux.io/bijux-canon/04-bijux-canon-reason/`,
  `https://bijux.io/bijux-canon/05-bijux-canon-agent/`, or
  `https://bijux.io/bijux-canon/06-bijux-canon-runtime/`
- inspect compatibility package metadata if the question is about what remains preserved
- continue to `https://bijux.io/bijux-canon/08-compat-packages/migration/compatibility-overview/`
  when the question broadens from one import root to compatibility strategy

## Honesty Boundary

This section documents preserved legacy surfaces, but it does not claim those legacy names are the preferred place for new work or long-term design growth. If a legacy name remains, that is a migration fact, not a design endorsement.

## Purpose

This page shows which Python import names remain preserved.

## Stability

Keep it aligned with the `src/` roots inside the compatibility packages.
