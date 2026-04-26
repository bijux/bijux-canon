---
title: Command Surfaces
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-04
---

# Command Surfaces

Some compatibility packages also preserve historic command names so migration
does not break operator scripts immediately.

A preserved command is a safety rail on the way to the canonical package, not a
new invitation to stay on the old name forever.

## Visual Summary

```mermaid
flowchart TB
    scripts["Existing operator scripts"]
    legacy1["agentic-flows"]
    legacy2["bijux-agent"]
    legacy3["bijux-rag"]
    legacy4["bijux-rar"]
    legacy5["bijux-vex"]
    canon1["bijux-canon-runtime CLI"]
    canon2["bijux-canon-agent CLI"]
    canon3["bijux-canon-ingest CLI"]
    canon4["bijux-canon-reason CLI"]
    canon5["bijux-canon-index CLI"]
    review["Retire the old command names<br/>when automation has moved"]
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    classDef action fill:var(--bijux-mermaid-action-fill),stroke:var(--bijux-mermaid-action-stroke),color:var(--bijux-mermaid-action-text);
    scripts --> legacy1
    scripts --> legacy2
    scripts --> legacy3
    scripts --> legacy4
    scripts --> legacy5
    legacy1 --> canon1
    legacy2 --> canon2
    legacy3 --> canon3
    legacy4 --> canon4
    legacy5 --> canon5
    canon1 --> review
    canon2 --> review
    canon3 --> review
    canon4 --> review
    canon5 --> review
    class canon1,canon2,canon3,canon4,canon5 positive;
    class legacy1,legacy2,legacy3,legacy4,legacy5 caution;
    class scripts anchor;
    class review action;
```

## Command Rule

A compatibility command should only exist when the canonical package still
provides a meaningful route behind it.

## Concrete Anchors

- `packages/compat-*` for the preserved legacy packages
- the compatibility package `README.md` files for canonical targets
- the matching canonical package docs for current behavior and new work

## Open This Page When

- you are tracing a legacy package name back to its canonical replacement
- you need migration guidance rather than product implementation detail
- you are deciding whether a compatibility surface still deserves to exist

## Decision Rule

Use this page when the main question is whether a preserved command still
serves a real migration need. If the only reason to keep it is habit rather
than an identified dependent environment, plan migration or retirement instead.

## What This Page Answers

- which legacy commands are still preserved
- which canonical CLIs replace them
- what evidence would justify retiring a compatibility command surface

## Reviewer Lens

- compare legacy names here with the compatibility package metadata and README targets
- check that migration advice still points at current canonical docs
- confirm that compatibility language does not accidentally encourage new work to start here

## Next Checks

- open the canonical package docs once the current target package is known:
  `https://bijux.io/bijux-canon/02-bijux-canon-ingest/`,
  `https://bijux.io/bijux-canon/03-bijux-canon-index/`,
  `https://bijux.io/bijux-canon/04-bijux-canon-reason/`,
  `https://bijux.io/bijux-canon/05-bijux-canon-agent/`, or
  `https://bijux.io/bijux-canon/06-bijux-canon-runtime/`
- inspect compatibility package metadata if the question is about what remains preserved
- continue to `https://bijux.io/bijux-canon/08-compat-packages/migration/retirement-conditions/`
  when the question turns into retirement readiness

## Honesty Boundary

This section documents preserved legacy surfaces, but it does not claim those legacy names are the preferred place for new work or long-term design growth. If a legacy name remains, that is a migration fact, not a design endorsement.

