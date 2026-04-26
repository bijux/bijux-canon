---
title: Interfaces
audience: mixed
type: index
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-26
---

# Interfaces

This section explains which commands, APIs, imports, schemas, and artifacts `bijux-canon-runtime` is prepared to stand behind as real surfaces.

These pages explain the public face of `bijux-canon-runtime`. They help a
caller separate deliberate contracts from incidental visibility before a
dependency hardens around the wrong surface.

Runtime contracts matter because this package exposes governed execution and
replay surfaces that other packages, tools, and reviewers may treat as
authoritative. This section should make it obvious which commands, schemas,
artifacts, and imports are real promises.

## Visual Summary

```mermaid
flowchart LR
    reader["reader question<br/>what can I safely depend on?"]
    cli["CLI and operator entrypoints"]
    api["HTTP and schema surfaces"]
    artifacts["replay envelopes, stores, and output artifacts"]
    imports["public Python imports"]
    compatibility["what needs compatibility review"]
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    class reader page;
    class cli,api,artifacts,imports positive;
    class compatibility caution;
    reader --> cli
    reader --> api
    reader --> artifacts
    reader --> imports
    reader --> compatibility
```

## Start Here

- open [CLI Surface](cli-surface.md) when the operator-facing run contract is
  the real dependency
- open [API Surface](api-surface.md) when the question is about HTTP behavior
  or frozen schemas
- open [Artifact Contracts](artifact-contracts.md) when durable run records or
  replay outputs matter more than commands
- open [Compatibility Commitments](compatibility-commitments.md) before
  changing names, shapes, or schema surfaces that another package may depend on

## Pages in This Section

- [CLI Surface](cli-surface.md)
- [API Surface](api-surface.md)
- [Configuration Surface](configuration-surface.md)
- [Data Contracts](data-contracts.md)
- [Artifact Contracts](artifact-contracts.md)
- [Entrypoints and Examples](entrypoints-and-examples.md)
- [Operator Workflows](operator-workflows.md)
- [Public Imports](public-imports.md)
- [Compatibility Commitments](compatibility-commitments.md)

## Use This Page When

- you need the public command, API, import, schema, or artifact surface
- you are checking whether a caller can safely rely on a given entrypoint or shape
- you want the contract-facing side of the package before building on it

## Do Not Use This Section When

- the real question is why runtime owns a behavior rather than a lower package
- you need execution structure or storage layering before judging a surface
- you are deciding whether the current proof is strong enough rather than which
  contract exists

## Concrete Anchors

- `src/bijux_canon_runtime/interfaces/cli/entrypoint.py` and
  `src/bijux_canon_runtime/interfaces/cli/parser.py` for operator entrypoints
- `src/bijux_canon_runtime/api/v1/` plus `apis/bijux-canon-runtime/v1/` for
  the HTTP and schema contract surface
- `src/bijux_canon_runtime/contracts/` and
  `src/bijux_canon_runtime/model/execution/replay_envelope.py` for durable
  artifact and data contracts
- `tests/api/test_schema_stability.py` and `tests/unit/contracts/` for
  interface-facing proof

## Read Across The Package

- open [Architecture](../architecture/index.md) when a surface question becomes
  a module or storage question
- open [Operations](../operations/index.md) when a contract depends on a
  repeatable workflow, migration, or release path
- open [Quality](../quality/index.md) when the real question is whether the
  interface is sufficiently defended

## Reader Takeaway

Use `Interfaces` to decide whether a caller-facing surface is explicit enough to
depend on. If the surface cannot be tied back to code, frozen schemas, named
artifacts, examples, and tests, treat it as unstable until that evidence is
visible.

## Purpose

This page explains how to use the interfaces section for
`bijux-canon-runtime` without repeating the detail that belongs on the topic
pages beneath it.
