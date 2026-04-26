---
title: Interfaces
audience: mixed
type: index
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-04-26
---

# Interfaces

Use this section when the question is what another package, tool, or operator
can safely rely on from `bijux-canon-reason`: commands, HTTP routes, schema
shapes, trace formats, artifacts, and public imports.

This package carries more contract pressure than an internal helper library
because its outputs are designed to be inspected, replayed, and challenged. A
reasoning trace or verification artifact is not just “something the code wrote”;
it is part of the evidence a later reader may depend on.

## Visual Summary

```mermaid
flowchart LR
    cli["CLI entrypoints and replay commands"]
    api["HTTP routes and OpenAPI shapes"]
    traces["canonical JSON and trace JSONL formats"]
    artifacts["run artifacts and evidence outputs"]
    imports["public Python imports"]
    reader["reader question<br/>which reasoning surfaces are real contracts?"]
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    class cli,page reader;
    class api,traces positive;
    class artifacts,imports anchor;
    class cli --> reader
    api --> reader
    traces --> reader
    artifacts --> reader
    imports --> reader
```

## Start Here

- open [CLI Surface](cli-surface.md) for operator-facing commands and replay
  entrypoints
- open [API Surface](api-surface.md) when the contract is HTTP-facing rather
  than terminal-facing
- open [Artifact Contracts](artifact-contracts.md) and
  [Data Contracts](data-contracts.md) when the durable output shape matters
  more than the call syntax

## Pages In This Section

- [CLI Surface](cli-surface.md)
- [API Surface](api-surface.md)
- [Configuration Surface](configuration-surface.md)
- [Data Contracts](data-contracts.md)
- [Artifact Contracts](artifact-contracts.md)
- [Entrypoints and Examples](entrypoints-and-examples.md)
- [Operator Workflows](operator-workflows.md)
- [Public Imports](public-imports.md)
- [Compatibility Commitments](compatibility-commitments.md)

## Use This Section When

- you need to know whether a command, route, schema, trace file, or import is
  meant to be stable
- a change may affect replayability, artifact reading, or downstream contract
  assumptions
- a reviewer needs to separate explicit interfaces from incidental visibility

## Do Not Use This Section When

- the real question is why the behavior belongs in reasoning at all
- the concern is mainly how the package is organized internally
- the issue is procedural or proof-oriented rather than contract-oriented

## Read Across The Package

- open [Foundation](../foundation/index.md) for package purpose and ownership
- open [Architecture](../architecture/index.md) for structural seams behind the
  public surfaces
- open [Operations](../operations/index.md) for install, replay, and release
  procedures
- open [Quality](../quality/index.md) for compatibility evidence and review
  pressure

## Concrete Anchors

- `src/bijux_canon_reason/interfaces/cli` for command entrypoints
- `src/bijux_canon_reason/api/v1` for HTTP routes and models
- `src/bijux_canon_reason/interfaces/serialization` for canonical JSON and
  trace JSONL formats
- `apis/bijux-canon-reason/v1/schema.yaml` for the published schema contract

## Reader Takeaway

Use `Interfaces` to judge whether a dependency is defensible. In this package,
the answer is not just “is there a function for it?” but also “can a reviewer
trace the contract through commands, schemas, artifacts, examples, and tests?”

## Purpose

This page introduces the reasoning interfaces handbook and routes readers to
the pages that explain commands, APIs, artifacts, imports, and compatibility
commitments.
