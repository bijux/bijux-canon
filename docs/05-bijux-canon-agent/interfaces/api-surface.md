---
title: API Surface
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-04-04
---

# API Surface

HTTP-facing behavior should be discoverable from tracked schema files and the
owning API modules.

The goal of this page is clarity before code-reading. A reviewer should be able
to see which API assets matter, where they live, and why a caller would treat
them as stable enough to depend on.

Treat the interfaces pages for `bijux-canon-agent` as the bridge between implementation detail and caller expectation. They should show what the package is prepared to defend before a dependency forms.

## Visual Summary

```mermaid
flowchart TB
    page["API Surface<br/>clarifies: identify contracts | see caller impact | review compatibility"]
    classDef page fill:#dbeafe,stroke:#1d4ed8,color:#1e3a8a,stroke-width:2px;
    classDef positive fill:#dcfce7,stroke:#16a34a,color:#14532d;
    classDef caution fill:#fee2e2,stroke:#dc2626,color:#7f1d1d;
    classDef anchor fill:#ede9fe,stroke:#7c3aed,color:#4c1d95;
    classDef action fill:#fef3c7,stroke:#d97706,color:#7c2d12;
    surface1["CLI entrypoint in src/bijux_canon_agent/interfaces/cli/entrypoint.py"]
    surface1 --> page
    surface2["operator configuration under src/bijux_canon_agent/config"]
    surface2 --> page
    surface3["HTTP-adjacent modules under src/bijux_canon_agent/api"]
    surface3 --> page
    proof1["trace-backed final outputs"]
    page --> proof1
    proof2["workflow graph execution records"]
    page --> proof2
    proof3["apis/bijux-canon-agent/v1/schema.yaml"]
    page --> proof3
    review1["tests/unit for local behavior and utility coverage"]
    review1 -.raises compatibility pressure on.-> page
    review2["tests/integration and tests/e2e for end-to-end workflow behavior"]
    review2 -.raises compatibility pressure on.-> page
    review3["tests/invariants for package promises that should not drift"]
    review3 -.raises compatibility pressure on.-> page
    class page page;
    class surface1,surface2,surface3 positive;
    class proof1,proof2,proof3 anchor;
    class review1,review2,review3 caution;
```

## API Artifacts

- apis/bijux-canon-agent/v1/schema.yaml

## Boundary Modules

- CLI entrypoint in src/bijux_canon_agent/interfaces/cli/entrypoint.py
- operator configuration under src/bijux_canon_agent/config
- HTTP-adjacent modules under src/bijux_canon_agent/api

## Concrete Anchors

- CLI entrypoint in src/bijux_canon_agent/interfaces/cli/entrypoint.py
- operator configuration under src/bijux_canon_agent/config
- HTTP-adjacent modules under src/bijux_canon_agent/api
- apis/bijux-canon-agent/v1/schema.yaml

## Use This Page When

- you need the public command, API, import, schema, or artifact surface
- you are checking whether a caller can safely rely on a given entrypoint or shape
- you want the contract-facing side of the package before building on it

## Decision Rule

Use `API Surface` to decide whether a caller-facing surface is explicit enough to depend on. If the surface cannot be tied back to concrete code, schemas, artifacts, examples, and tests, treat it as unstable until that evidence is visible.

## What This Page Answers

- which public or operator-facing surfaces `bijux-canon-agent` is really asking readers to trust
- which schemas, artifacts, imports, or commands behave like contracts
- what compatibility pressure a change to this surface would create

## Reviewer Lens

- compare commands, schemas, imports, and artifacts against the documented surface one by one
- check whether a seemingly local change actually needs compatibility review
- confirm that examples still point to real entrypoints and not to stale habits

## Honesty Boundary

This page can identify the intended public surfaces of `bijux-canon-agent`, but real compatibility depends on code, schemas, artifacts, examples, and tests staying aligned. If those disagree, the prose is wrong or incomplete.

## Next Checks

- move to operations when the caller-facing question becomes procedural or environmental
- move to quality when compatibility or evidence of protection becomes the real issue
- move back to architecture when a public-surface question reveals a deeper structural drift

## Purpose

This page ties API behavior to tracked code and schema assets.

## Stability

Keep it aligned with the actual API modules and schema files.
