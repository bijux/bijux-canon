---
title: Interfaces
audience: mixed
type: index
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-04-26
---

# Interfaces

Open this section when the question is what another package, tool, or operator
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

- open [CLI Surface](https://bijux.io/bijux-canon/04-bijux-canon-reason/interfaces/cli-surface/) for operator-facing commands and replay
  entrypoints
- open [API Surface](https://bijux.io/bijux-canon/04-bijux-canon-reason/interfaces/api-surface/) when the contract is HTTP-facing rather
  than terminal-facing
- open [Artifact Contracts](https://bijux.io/bijux-canon/04-bijux-canon-reason/interfaces/artifact-contracts/) and
  [Data Contracts](https://bijux.io/bijux-canon/04-bijux-canon-reason/interfaces/data-contracts/) when the durable output shape matters
  more than the call syntax

## Pages In This Section

- [CLI Surface](https://bijux.io/bijux-canon/04-bijux-canon-reason/interfaces/cli-surface/)
- [API Surface](https://bijux.io/bijux-canon/04-bijux-canon-reason/interfaces/api-surface/)
- [Configuration Surface](https://bijux.io/bijux-canon/04-bijux-canon-reason/interfaces/configuration-surface/)
- [Data Contracts](https://bijux.io/bijux-canon/04-bijux-canon-reason/interfaces/data-contracts/)
- [Artifact Contracts](https://bijux.io/bijux-canon/04-bijux-canon-reason/interfaces/artifact-contracts/)
- [Entrypoints and Examples](https://bijux.io/bijux-canon/04-bijux-canon-reason/interfaces/entrypoints-and-examples/)
- [Operator Workflows](https://bijux.io/bijux-canon/04-bijux-canon-reason/interfaces/operator-workflows/)
- [Public Imports](https://bijux.io/bijux-canon/04-bijux-canon-reason/interfaces/public-imports/)
- [Compatibility Commitments](https://bijux.io/bijux-canon/04-bijux-canon-reason/interfaces/compatibility-commitments/)

## Open Interfaces When

- you need to know whether a command, route, schema, trace file, or import is
  meant to be stable
- a change may affect replayability, artifact reading, or downstream contract
  assumptions
- a reviewer needs to separate explicit interfaces from incidental visibility

## Open Another Section When

- the real question is why the behavior belongs in reasoning at all
- the concern is mainly how the package is organized internally
- the issue is procedural or proof-oriented rather than contract-oriented

## Read Across The Package

- open [Foundation](https://bijux.io/bijux-canon/04-bijux-canon-reason/foundation/) for package purpose and ownership
- open [Architecture](https://bijux.io/bijux-canon/04-bijux-canon-reason/architecture/) for structural seams behind the
  public surfaces
- open [Operations](https://bijux.io/bijux-canon/04-bijux-canon-reason/operations/) for install, replay, and release
  procedures
- open [Quality](https://bijux.io/bijux-canon/04-bijux-canon-reason/quality/) for compatibility evidence and review
  pressure

## Concrete Anchors

- `src/bijux_canon_reason/interfaces/cli` for command entrypoints
- `src/bijux_canon_reason/api/v1` for HTTP routes and models
- `src/bijux_canon_reason/interfaces/serialization` for canonical JSON and
  trace JSONL formats
- `apis/bijux-canon-reason/v1/schema.yaml` for the published schema contract

## Bottom Line

Open `Interfaces` to judge whether a dependency is defensible. In this package,
the answer is not just “is there a function for it?” but also “can a reviewer
trace the contract through commands, schemas, artifacts, examples, and tests?”

## What You Get

Open this page when you need the command, API, artifact, import, and
compatibility route through `bijux-canon-reason` before you inspect a specific
contract surface.
