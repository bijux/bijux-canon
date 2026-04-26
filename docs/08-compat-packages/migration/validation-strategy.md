---
title: Validation Strategy
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-04
---

# Validation Strategy

Compatibility packages are small, but they still need validation for import
preservation, packaging metadata, and migration pointers.

Small does not mean unimportant. These packages carry trust mainly through
naming continuity, so the validation has to prove that the bridge still
points to the right place.

## Visual Summary

```mermaid
flowchart LR
    compat["Compatibility package"]
    importCheck["Check the legacy import root<br/>still resolves"]
    commandCheck["Check the legacy command<br/>still reaches the canonical CLI"]
    docsCheck["Check README and docs<br/>still point at the canonical target"]
    gate["Bridge still works<br/>and still serves a supported need"]
    release["Keep the package releasable"]
    retire["If the bridge is no longer needed,<br/>plan retirement instead of patching forever"]
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    classDef action fill:var(--bijux-mermaid-action-fill),stroke:var(--bijux-mermaid-action-stroke),color:var(--bijux-mermaid-action-text);
    compat --> importCheck
    compat --> commandCheck
    compat --> docsCheck
    importCheck --> gate
    commandCheck --> gate
    docsCheck --> gate
    gate -- yes --> release
    gate -- no --> retire
    class compat,gate page;
    class release positive;
    class importCheck,commandCheck caution;
    class docsCheck anchor;
    class retire action;
```

## Validation Focus

- import resolution
- packaging metadata correctness
- links and references to the canonical package docs

## Concrete Anchors

- `packages/compat-*` for the preserved legacy packages
- the compatibility package `README.md` files for canonical targets
- the matching canonical package docs for current behavior and new work

## Open This Page When

- you are tracing a legacy package name back to its canonical replacement
- you need migration guidance rather than product implementation detail
- you are deciding whether a compatibility surface still deserves to exist

## Decision Rule

Use this page when the main question is what evidence keeps a compatibility
package trustworthy. If the only reason to keep a preserved name is habit
rather than a supported dependent environment, plan migration or retirement
instead.

## What You Can Resolve Here

- which validation signals keep the bridge trustworthy
- when new work should open the canonical package instead
- what evidence would justify retiring a compatibility package

## Review Focus

- compare legacy names here with the compatibility package metadata and README targets
- check that migration advice still points at current canonical docs
- confirm that compatibility language does not accidentally encourage new work to start here

## Read Next

- open the canonical package docs once the current target package is known:
  `https://bijux.io/bijux-canon/02-bijux-canon-ingest/`,
  `https://bijux.io/bijux-canon/03-bijux-canon-index/`,
  `https://bijux.io/bijux-canon/04-bijux-canon-reason/`,
  `https://bijux.io/bijux-canon/05-bijux-canon-agent/`, or
  `https://bijux.io/bijux-canon/06-bijux-canon-runtime/`
- inspect compatibility package metadata if the question is about what remains preserved
- continue to `https://bijux.io/bijux-canon/08-compat-packages/migration/retirement-conditions/`
  when validation shows the bridge may be ready for retirement

## Limits

This section documents preserved legacy surfaces, but it does not claim those legacy names are the preferred place for new work or long-term design growth. If a legacy name remains, that is a migration fact, not a design endorsement.

