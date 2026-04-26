---
title: Interfaces
audience: mixed
type: index
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-26
---

# Interfaces

Open this section when you need to know which index-facing surfaces are real
contracts: retrieval commands, APIs, schemas, imports, artifacts, and
examples that other packages or operators can safely rely on.

These pages prevent accidental dependencies from forming around internal
backend details or transient implementation choices. For index, that matters
because once retrieval contracts spread into reasoning or runtime, later
corrections become expensive.

## Visual Summary

```mermaid
flowchart LR
    caller["reader or downstream caller"]
    cli["CLI workflows<br/>query, build, replay"]
    api["APIs and schemas<br/>retrieval-facing contracts"]
    artifacts["artifact contracts<br/>index files and outputs"]
    imports["public imports<br/>supported entrypoints"]
    review["compatibility review<br/>what changes need extra care"]
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    classDef action fill:var(--bijux-mermaid-action-fill),stroke:var(--bijux-mermaid-action-stroke),color:var(--bijux-mermaid-action-text);
    class caller,page review;
    class cli,api,artifacts positive;
    class imports anchor;
    class review action;
    caller --> cli
    caller --> api
    caller --> artifacts
    caller --> imports
    caller --> review
```

## Start Here

- open [CLI Surface](https://bijux.io/bijux-canon/03-bijux-canon-index/interfaces/cli-surface/) when the issue begins with a query, build,
  or replay command
- open [API Surface](https://bijux.io/bijux-canon/03-bijux-canon-index/interfaces/api-surface/) when the question is about HTTP or
  retrieval-facing service boundaries
- open [Data Contracts](https://bijux.io/bijux-canon/03-bijux-canon-index/interfaces/data-contracts/) when schemas or payload shapes are
  the real dependency
- open [Compatibility Commitments](https://bijux.io/bijux-canon/03-bijux-canon-index/interfaces/compatibility-commitments/) when a change
  may break a retrieval contract that others already trust

## Pages In Interfaces

- [CLI Surface](https://bijux.io/bijux-canon/03-bijux-canon-index/interfaces/cli-surface/)
- [API Surface](https://bijux.io/bijux-canon/03-bijux-canon-index/interfaces/api-surface/)
- [Configuration Surface](https://bijux.io/bijux-canon/03-bijux-canon-index/interfaces/configuration-surface/)
- [Data Contracts](https://bijux.io/bijux-canon/03-bijux-canon-index/interfaces/data-contracts/)
- [Artifact Contracts](https://bijux.io/bijux-canon/03-bijux-canon-index/interfaces/artifact-contracts/)
- [Entrypoints and Examples](https://bijux.io/bijux-canon/03-bijux-canon-index/interfaces/entrypoints-and-examples/)
- [Operator Workflows](https://bijux.io/bijux-canon/03-bijux-canon-index/interfaces/operator-workflows/)
- [Public Imports](https://bijux.io/bijux-canon/03-bijux-canon-index/interfaces/public-imports/)
- [Compatibility Commitments](https://bijux.io/bijux-canon/03-bijux-canon-index/interfaces/compatibility-commitments/)

## Open Interfaces When

- you need to know which retrieval surfaces are intentional and supportable
- downstream reasoning or runtime behavior depends on index commands, schemas,
  artifacts, or imports
- you are reviewing whether a change creates compatibility pressure on a public
  surface

## Open Another Section When

- the real question is why retrieval ownership belongs in index at all
- you need internal layering, state flow, or backend structure first
- the problem is operational, such as setup, diagnostics, or release handling

## Read Across The Package

- open [Foundation](https://bijux.io/bijux-canon/03-bijux-canon-index/foundation/) when a contract concern is really a
  package-boundary concern
- open [Architecture](https://bijux.io/bijux-canon/03-bijux-canon-index/architecture/) when the surface depends on
  deeper retrieval structure or backend layering
- open [Operations](https://bijux.io/bijux-canon/03-bijux-canon-index/operations/) when the contract question starts
  with a repeatable maintainer workflow
- open [Quality](https://bijux.io/bijux-canon/03-bijux-canon-index/quality/) when the real issue is whether the
  documented contract is sufficiently defended

## Concrete Anchors

- CLI modules under `src/bijux_canon_index/interfaces/cli`
- HTTP app under `src/bijux_canon_index/api`
- OpenAPI schema files under `apis/bijux-canon-index/v1`
- `apis/bijux-canon-index/v1/schema.yaml`

## Why Use Interfaces

Open `Interfaces` to separate supported retrieval contracts from internal index
visibility. If a dependency cannot be defended in terms of named commands,
schemas, artifacts, examples, and tests, it is not yet a stable public surface.

## What You Get

Open this page when you need the command, API, artifact, and compatibility
route through `bijux-canon-index` before you inspect a specific interface
surface.
