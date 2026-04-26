---
title: Foundation
audience: mixed
type: index
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-26
---

# Foundation

`bijux-canon-index` exists to turn ingest-ready material into searchable,
replayable retrieval behavior. Open this section when the important question is
why retrieval ownership lives here and where it stops before reasoning or
runtime take over.

These pages help you separate three different concerns that often get blurred
together: ingest preparation, index execution, and reasoning over retrieved
results. Open them when you need a clear package boundary before changing code
or contracts.

## Start Here

- open [Package Overview](https://bijux.io/bijux-canon/03-bijux-canon-index/foundation/package-overview/) for the shortest explanation of
  what the index package is for
- open [Ownership Boundary](https://bijux.io/bijux-canon/03-bijux-canon-index/foundation/ownership-boundary/) when retrieval behavior may
  be confused with ingest preparation or reasoning semantics
- open [Lifecycle Overview](https://bijux.io/bijux-canon/03-bijux-canon-index/foundation/lifecycle-overview/) when the key question is how
  prepared material becomes a replayable retrieval surface

## Pages In This Section

- [Package Overview](https://bijux.io/bijux-canon/03-bijux-canon-index/foundation/package-overview/)
- [Scope and Non-Goals](https://bijux.io/bijux-canon/03-bijux-canon-index/foundation/scope-and-non-goals/)
- [Ownership Boundary](https://bijux.io/bijux-canon/03-bijux-canon-index/foundation/ownership-boundary/)
- [Repository Fit](https://bijux.io/bijux-canon/03-bijux-canon-index/foundation/repository-fit/)
- [Capability Map](https://bijux.io/bijux-canon/03-bijux-canon-index/foundation/capability-map/)
- [Domain Language](https://bijux.io/bijux-canon/03-bijux-canon-index/foundation/domain-language/)
- [Lifecycle Overview](https://bijux.io/bijux-canon/03-bijux-canon-index/foundation/lifecycle-overview/)
- [Dependencies and Adjacencies](https://bijux.io/bijux-canon/03-bijux-canon-index/foundation/dependencies-and-adjacencies/)
- [Change Principles](https://bijux.io/bijux-canon/03-bijux-canon-index/foundation/change-principles/)

## Open Foundation When

- you need the durable ownership story behind embeddings, retrieval, and replay
- you are deciding whether work belongs in index or in the packages before or
  after it
- you need shared package language for retrieval behavior before reading code or
  contracts

## Open Another Section When

- the question is already about a command, schema, artifact, or import surface
- the real issue is operational, such as local setup, diagnostics, or release
- you already know the boundary and need proof, risks, or validation instead

## Read Across The Package

- open [Architecture](https://bijux.io/bijux-canon/03-bijux-canon-index/architecture/) when you need the structural
  map behind domain, application, and infrastructure flow
- open [Interfaces](https://bijux.io/bijux-canon/03-bijux-canon-index/interfaces/) when the question is about public
  retrieval contracts
- open [Operations](https://bijux.io/bijux-canon/03-bijux-canon-index/operations/) when you need setup, local
  workflows, or release guidance
- open [Quality](https://bijux.io/bijux-canon/03-bijux-canon-index/quality/) when you need evidence that replay and
  retrieval behavior are actually protected

## Concrete Anchors

- `packages/bijux-canon-index` as the package root
- `packages/bijux-canon-index/src/bijux_canon_index` as the import boundary
- `packages/bijux-canon-index/tests` as the proof surface for owned behavior

## Bottom Line

Open `Foundation` to answer the ownership question with integrity: index exists
to make retrieval behavior explicit, replayable, and dependable enough for
downstream packages to use. If a proposed change broadens the package without
making that retrieval story clearer, it is probably crossing a boundary rather
than improving the design.

