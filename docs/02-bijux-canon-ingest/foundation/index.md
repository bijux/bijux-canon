---
title: Foundation
audience: mixed
type: index
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-04-26
---

# Foundation

`bijux-canon-ingest` exists to turn raw source material into deterministic,
retrieval-ready output. Open this section when the important question is not
which command to run, but why ingest owns this work at all and where that
ownership stops.

These pages help you distinguish source preparation from the downstream jobs
that index, reason over, or orchestrate the prepared output. Open them when
you need a clear explanation of why ingest exists without relying on tribal
memory.

## Start Here

- open [Package Overview](https://bijux.io/bijux-canon/02-bijux-canon-ingest/foundation/package-overview/) for the shortest explanation of
  what ingest is for
- open [Ownership Boundary](https://bijux.io/bijux-canon/02-bijux-canon-ingest/foundation/ownership-boundary/) when the issue might belong
  in index, reason, agent, or runtime instead
- open [Lifecycle Overview](https://bijux.io/bijux-canon/02-bijux-canon-ingest/foundation/lifecycle-overview/) when the real question is
  how source material moves through ingest before downstream packages pick it up

## Pages In This Section

- [Package Overview](https://bijux.io/bijux-canon/02-bijux-canon-ingest/foundation/package-overview/)
- [Scope and Non-Goals](https://bijux.io/bijux-canon/02-bijux-canon-ingest/foundation/scope-and-non-goals/)
- [Ownership Boundary](https://bijux.io/bijux-canon/02-bijux-canon-ingest/foundation/ownership-boundary/)
- [Repository Fit](https://bijux.io/bijux-canon/02-bijux-canon-ingest/foundation/repository-fit/)
- [Capability Map](https://bijux.io/bijux-canon/02-bijux-canon-ingest/foundation/capability-map/)
- [Domain Language](https://bijux.io/bijux-canon/02-bijux-canon-ingest/foundation/domain-language/)
- [Lifecycle Overview](https://bijux.io/bijux-canon/02-bijux-canon-ingest/foundation/lifecycle-overview/)
- [Dependencies and Adjacencies](https://bijux.io/bijux-canon/02-bijux-canon-ingest/foundation/dependencies-and-adjacencies/)
- [Change Principles](https://bijux.io/bijux-canon/02-bijux-canon-ingest/foundation/change-principles/)

## Open This Section When

- you need the durable ownership story before reading code or command docs
- you are deciding whether deterministic preparation belongs in ingest or
  downstream retrieval behavior belongs elsewhere
- you need shared package language for chunking, source shaping, and handoff

## Open Another Section When

- the question is already about public commands, schemas, or artifact contracts
- the real problem is operational, such as setup, diagnostics, or release flow
- you already know the boundary and need proof, tests, or risk review instead

## Across This Package

- open [Architecture](https://bijux.io/bijux-canon/02-bijux-canon-ingest/architecture/) when you need the structure
  behind ingest preparation and workflow flow
- open [Interfaces](https://bijux.io/bijux-canon/02-bijux-canon-ingest/interfaces/) when you need the contracts that
  callers and downstream packages rely on
- open [Operations](https://bijux.io/bijux-canon/02-bijux-canon-ingest/operations/) when you need local workflow,
  validation, or release guidance
- open [Quality](https://bijux.io/bijux-canon/02-bijux-canon-ingest/quality/) when you need evidence that deterministic
  ingest behavior is actually protected

## Concrete Anchors

- `packages/bijux-canon-ingest` as the package root
- `packages/bijux-canon-ingest/src/bijux_canon_ingest` as the import boundary
- `packages/bijux-canon-ingest/tests` as the proof surface for owned behavior

## Bottom Line

Open this section to answer the ownership question with integrity: ingest exists
to make source material predictable enough for downstream retrieval work to
trust. If a proposal broadens ingest without making that preparation story
clearer, the design has probably crossed the boundary rather than improved it.

