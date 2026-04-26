---
title: Execution Model
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-04
---

# Execution Model

`bijux-canon-runtime` executes work by receiving inputs at its interfaces, coordinating policy
and workflows in application code, and delegating specific responsibilities to
owned modules.

This page shows one clean story about how work moves through the package. The
goal is not to describe every branch, but to make the main path recognizable
before someone opens the implementation.

The architecture pages are a reviewer-facing map of structure and flow. They shorten code reading instead of replacing it.

## Visual Summary

```mermaid
flowchart LR
    input["Entrypoint<br/>CLI entrypoint in src/bijux_canon_runtime/interfaces/cli/entrypoint.py"]
    workflow["Workflow<br/>runtime<br/>execution engines and lifecycle"]
    rules["Core decisions<br/>model<br/>durable runtime models"]
    output["Visible result<br/>execution store records"]
    input --> workflow --> rules --> output
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    classDef action fill:var(--bijux-mermaid-action-fill),stroke:var(--bijux-mermaid-action-stroke),color:var(--bijux-mermaid-action-text);
    class input anchor;
    class workflow positive;
    class rules page;
    class output action;
```

## Execution Anchors

- entry surfaces: CLI entrypoint in src/bijux_canon_runtime/interfaces/cli/entrypoint.py, HTTP app in src/bijux_canon_runtime/api/v1, schema files in apis/bijux-canon-runtime/v1
- workflow modules: src/bijux_canon_runtime/model, src/bijux_canon_runtime/runtime, src/bijux_canon_runtime/application
- outputs: execution store records, replay decision artifacts, non-determinism policy evaluations

## Concrete Anchors

- `src/bijux_canon_runtime/model` for durable runtime models
- `src/bijux_canon_runtime/runtime` for execution engines and lifecycle logic
- `src/bijux_canon_runtime/application` for orchestration and replay coordination

## Open This Page When

- you are tracing structure, execution flow, or dependency pressure
- you need to understand how modules fit before refactoring
- you are reviewing design drift rather than one isolated bug

## Decision Rule

Use `Execution Model` to decide whether a structural change makes `bijux-canon-runtime` easier or harder to explain in terms of modules, dependency direction, and execution flow. If the change works only because the design becomes harder to read, the safer answer is redesign rather than acceptance.

## What You Can Resolve Here

- how `bijux-canon-runtime` is organized internally in terms a reviewer can follow
- which modules carry the main execution and dependency story
- where structural drift would show up before it becomes expensive

## Review Focus

- trace the described execution path through the named modules instead of trusting the diagram alone
- look for dependency direction or layering that now contradicts the documented seam
- verify that the structural risks named here still match the current code shape

## Limits

Treat this page as a working structural map and keep it aligned with code and tests.

## Read Next

- open interfaces when the review reaches a public or operator-facing seam
- open operations when the concern becomes repeatable runtime behavior
- open quality when you need proof that the documented structure is still protected

