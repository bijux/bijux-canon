---
title: Repository Scope
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-04
---

# Repository Scope

The repository root is intentionally narrow. It exists to coordinate packages
that must move together, not to become a second implementation layer above
them.

A good scope test is simple: if a question can be answered honestly from one
package handbook, it probably does not belong at the root. Root scope should
stay reserved for rules, assets, and workflows that genuinely sit across
package boundaries.

## Visual Summary

```mermaid
flowchart LR
    root["Root ownership"]
    shared["Shared only<br/>layout, docs rules, schema governance"]
    packages["Product packages<br/>behavior and public contracts"]
    maintain["Maintenance surfaces<br/>automation and repository health"]
    root --> shared
    root --> packages
    root --> maintain
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    classDef action fill:var(--bijux-mermaid-action-fill),stroke:var(--bijux-mermaid-action-stroke),color:var(--bijux-mermaid-action-text);
    class root page;
    class shared positive;
    class packages caution;
    class maintain anchor;
```

## In Scope

- workspace-level build and test orchestration
- documentation, governance, and contributor-facing repository rules
- API schema storage and drift checks that involve multiple packages
- release tagging and versioning conventions shared across packages

## Out of Scope

- package-local domain behavior that belongs inside a package handbook
- hidden root logic that bypasses package APIs
- undocumented exceptions to the published package boundaries

## Concrete Anchors

- `pyproject.toml` for workspace metadata and commit conventions
- `Makefile` and `makes/` for root automation
- `apis/` and `.github/workflows/` for schema and validation review

## Open This Page When

- you are dealing with repository-wide seams rather than one package alone
- you need shared workflow, schema, or governance context before changing code
- you want the monorepo view that sits above the package handbooks

## Decision Rule

Use this page when the main question is whether a concern belongs at the
repository root at all. If one package handbook can answer it honestly, that
package should stay the owner.

## What This Page Answers

- which concerns belong at the repository root
- which shared assets and workflows justify root ownership
- how repository scope differs from package-local ownership

## Reviewer Lens

- compare the page claims with the real root files, workflows, or schema assets
- check that repository guidance still stops where package ownership begins
- confirm that any repository rule described here is still enforceable in code or automation

## Honesty Boundary

This page sets the ownership boundary, but package-local docs, code, schemas,
and tests still define the details on the package side of that boundary.

## Next Checks

- open the owning package docs when the question stops being repository-wide
- check root files, schemas, or workflows named here before trusting prose alone
- use the maintainer handbook at `https://bijux.io/bijux-canon/07-bijux-canon-maintain/`
  when the issue is really about automation or drift tooling

