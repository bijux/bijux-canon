---
title: Compatibility Commitments
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-04-04
---

# Compatibility Commitments

Compatibility in `bijux-canon-reason` should be explicit: stable commands, tracked schemas,
durable artifacts, and release notes that explain intentional breakage.

A realistic sense of the compatibility bar matters more than sounding generously stable while leaving the real boundary ambiguous.


## Visual Summary

```mermaid
flowchart LR
    change["Surface change"]
    contract["Check docs and schema<br/>apis/bijux-canon-reason/v1/schema.yaml"]
    proof["Run owning proof<br/>tests/perf for retrieval benchmark coverage"]
    release["Explain in release notes<br/>CHANGELOG.md<br/>pyproject.toml"]
    change --> contract --> proof --> release
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    classDef action fill:var(--bijux-mermaid-action-fill),stroke:var(--bijux-mermaid-action-stroke),color:var(--bijux-mermaid-action-text);
    class change page;
    class contract anchor;
    class proof positive;
    class release action;
```

## Compatibility Anchors

- README.md
- CHANGELOG.md
- pyproject.toml

## Review Rule

Breaking changes must be visible in code, docs, and validation together.

## Concrete Anchors

- CLI app in src/bijux_canon_reason/interfaces/cli
- HTTP app in src/bijux_canon_reason/api/v1
- schema files in apis/bijux-canon-reason/v1
- apis/bijux-canon-reason/v1/schema.yaml

## Open This Page When

- you need the public command, API, import, schema, or artifact surface
- you are checking whether a caller can safely rely on a given entrypoint or shape
- you want the contract-facing side of the package before building on it

## Decision Rule

Use this page when deciding whether a caller-facing surface is explicit enough to depend on. If the surface cannot be tied back to concrete code, schemas, artifacts, examples, and tests, treat it as unstable until that evidence is visible.

## What This Page Answers

- which public or operator-facing surfaces `bijux-canon-reason` is really asking readers to trust
- which schemas, artifacts, imports, or commands behave like contracts
- what compatibility pressure a change to this surface would create

## Reviewer Lens

- compare commands, schemas, imports, and artifacts against the documented surface one by one
- check whether a seemingly local change actually needs compatibility review
- confirm that examples still point to real entrypoints and not to stale habits

## Honesty Boundary

This page can identify the intended public surfaces of `bijux-canon-reason`, but real compatibility depends on code, schemas, artifacts, examples, and tests staying aligned. If those disagree, the prose is wrong or incomplete.

## Next Checks

- open `https://bijux.io/bijux-canon/04-bijux-canon-reason/operations/` when the caller-facing question becomes procedural or environmental
- open `https://bijux.io/bijux-canon/04-bijux-canon-reason/quality/` when compatibility or evidence of protection becomes the real issue
- open `https://bijux.io/bijux-canon/04-bijux-canon-reason/architecture/` when a public-surface question reveals a deeper structural drift

## Purpose

This page shows what should trigger compatibility review for the package.

## Stability

Keep it aligned with the package's actual public surfaces and release process.
