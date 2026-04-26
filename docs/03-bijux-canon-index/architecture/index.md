---
title: Architecture
audience: mixed
type: index
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-26
---

# Architecture

Open this section when the important question is how index is assembled:
which layers own retrieval semantics, how application workflows coordinate
queries and updates, and where backend infrastructure stops being the package's
core logic.

These pages help you trace real retrieval flow through domain, application,
and infrastructure layers without reconstructing the design from imports
alone. The goal is to make architectural responsibility explicit enough to
review and evolve.

## Visual Summary

```mermaid
flowchart LR
    request["retrieval request or index update"]
    app["application workflows<br/>coordinate operations"]
    domain["domain logic<br/>retrieval, provenance, replay rules"]
    infra["infrastructure adapters<br/>backends and environment"]
    state["durable index state"]
    seams["integration seams<br/>ingest inputs and downstream consumers"]
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    class request,page state;
    class app,domain,infra positive;
    class seams caution;
    request --> app --> domain --> infra --> state
    request --> seams
    state --> seams
```

## Start Here

- use [Module Map](https://bijux.io/bijux-canon/03-bijux-canon-index/architecture/module-map/) for the fastest route to directory-level
  architectural ownership
- use [Execution Model](https://bijux.io/bijux-canon/03-bijux-canon-index/architecture/execution-model/) when the real question is how
  retrieval work moves through the package
- use [State and Persistence](https://bijux.io/bijux-canon/03-bijux-canon-index/architecture/state-and-persistence/) when index durability
  and replay behavior are the hard part
- use [Integration Seams](https://bijux.io/bijux-canon/03-bijux-canon-index/architecture/integration-seams/) when a change might blur the
  edges between ingest, index, and downstream consumers

## Pages In Architecture

- [Module Map](https://bijux.io/bijux-canon/03-bijux-canon-index/architecture/module-map/)
- [Dependency Direction](https://bijux.io/bijux-canon/03-bijux-canon-index/architecture/dependency-direction/)
- [Execution Model](https://bijux.io/bijux-canon/03-bijux-canon-index/architecture/execution-model/)
- [State and Persistence](https://bijux.io/bijux-canon/03-bijux-canon-index/architecture/state-and-persistence/)
- [Integration Seams](https://bijux.io/bijux-canon/03-bijux-canon-index/architecture/integration-seams/)
- [Error Model](https://bijux.io/bijux-canon/03-bijux-canon-index/architecture/error-model/)
- [Extensibility Model](https://bijux.io/bijux-canon/03-bijux-canon-index/architecture/extensibility-model/)
- [Code Navigation](https://bijux.io/bijux-canon/03-bijux-canon-index/architecture/code-navigation/)
- [Architecture Risks](https://bijux.io/bijux-canon/03-bijux-canon-index/architecture/architecture-risks/)

## Use Architecture When

- you need to trace retrieval structure before refactoring or extending the
  package
- you are checking whether backend integration still respects the intended layer
  boundaries
- you need to understand where replay and provenance logic really live

## Open Another Section When

- the question is mainly about public commands, imports, schemas, or artifacts
- the issue is operational, such as local setup, diagnostics, or release
- you need tests, risks, or validation criteria more than a structural map

## Read Across The Package

- use [Foundation](https://bijux.io/bijux-canon/03-bijux-canon-index/foundation/) when the structural question is
  really an ownership question
- use [Interfaces](https://bijux.io/bijux-canon/03-bijux-canon-index/interfaces/) when architecture reaches a
  caller-facing contract or retrieval surface
- use [Operations](https://bijux.io/bijux-canon/03-bijux-canon-index/operations/) when structure affects repeatable
  maintainer workflows
- use [Quality](https://bijux.io/bijux-canon/03-bijux-canon-index/quality/) when you need proof that the documented
  design is still defended in tests and review

## Concrete Anchors

- `src/bijux_canon_index/domain` for execution, provenance, and request
  semantics
- `src/bijux_canon_index/application` for workflow coordination
- `src/bijux_canon_index/infra` for backends, adapters, and runtime environment
  helpers

## Why Use Architecture

Open `Architecture` to make retrieval structure legible enough that a reviewer
can say which logic belongs to the domain, which belongs to workflow
coordination, and which belongs to adapters. If that answer is blurry, the
package is already accumulating architectural drift.

## What You Get

Open this page when you need the module, execution, state, seam, and risk
route through `bijux-canon-index` before you inspect a specific architectural
topic.
