---
title: CLI Surface
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-04
---

# CLI Surface

The CLI surface is the operator-facing command layer for `bijux-canon-runtime`. It identifies which commands are deliberate entrypoints and which ones are local implementation detail.

Command surfaces tend to become contracts early, because people script them,
share them in tickets, and paste them into automation. That contract status should stay visible instead of accidental.


## Visual Summary

```mermaid
flowchart LR
    operator["Operator or script"]
    command["Command<br/>bijux-canon-runtime"]
    modules["Owning boundary<br/>CLI entrypoint in src/bijux_canon_runtime/interfaces/cli/entrypoint.py"]
    proof["Where to confirm<br/>tests/e2e for governed flow behavior"]
    operator --> command --> modules --> proof
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    classDef action fill:var(--bijux-mermaid-action-fill),stroke:var(--bijux-mermaid-action-stroke),color:var(--bijux-mermaid-action-text);
    class operator positive;
    class command page;
    class modules anchor;
    class proof action;
```

## Command Facts

- canonical command: `bijux-canon-runtime`
- interface modules: CLI entrypoint in src/bijux_canon_runtime/interfaces/cli/entrypoint.py, HTTP app in src/bijux_canon_runtime/api/v1, schema files in apis/bijux-canon-runtime/v1

## Concrete Anchors

- CLI entrypoint in src/bijux_canon_runtime/interfaces/cli/entrypoint.py
- HTTP app in src/bijux_canon_runtime/api/v1
- schema files in apis/bijux-canon-runtime/v1
- apis/bijux-canon-runtime/v1/schema.yaml

## Use This Page When

- you need the public command, API, import, schema, or artifact surface
- you are checking whether a caller can safely rely on a given entrypoint or shape
- you want the contract-facing side of the package before building on it

## Decision Rule

Use this page when deciding whether a caller-facing surface is explicit enough to depend on. If the surface cannot be tied back to concrete code, schemas, artifacts, examples, and tests, treat it as unstable until that evidence is visible.

## What This Page Answers

- which public or operator-facing surfaces `bijux-canon-runtime` is really asking readers to trust
- which schemas, artifacts, imports, or commands behave like contracts
- what compatibility pressure a change to this surface would create

## Reviewer Lens

- compare commands, schemas, imports, and artifacts against the documented surface one by one
- check whether a seemingly local change actually needs compatibility review
- confirm that examples still point to real entrypoints and not to stale habits

## Honesty Boundary

This page can identify the intended public surfaces of `bijux-canon-runtime`, but real compatibility depends on code, schemas, artifacts, examples, and tests staying aligned. If those disagree, the prose is wrong or incomplete.

## Next Checks

- move to `https://bijux.io/bijux-canon/06-bijux-canon-runtime/operations/` when the caller-facing question becomes procedural or environmental
- move to `https://bijux.io/bijux-canon/06-bijux-canon-runtime/quality/` when compatibility or evidence of protection becomes the real issue
- move to `https://bijux.io/bijux-canon/06-bijux-canon-runtime/architecture/` when a public-surface question reveals a deeper structural drift

## Purpose

This page identifies the command entrypoints and their owning code.

## Stability

Keep it aligned with the declared scripts and the interface modules that implement them.
