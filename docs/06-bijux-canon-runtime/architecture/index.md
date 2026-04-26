---
title: Architecture
audience: mixed
type: index
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-26
---

# Architecture

Open this section to understand how `bijux_canon_runtime` is organized so a
reviewer can follow structure, dependency direction, and execution flow
without guessing.

These pages turn `bijux-canon-runtime` from a directory tree into a readable
design map. Use them when a structural change needs to be grounded in named
modules and real execution paths.

Runtime architecture matters because this package does not merely execute a
flow. It plans, governs, records, stores, verifies, and replays that flow
under explicit policy. The structure has to keep those concerns legible rather
than letting them collapse into one giant executor.

## Start Here

- open [Module Map](https://bijux.io/bijux-canon/06-bijux-canon-runtime/architecture/module-map/) for the shortest structural tour
- open [Execution Model](https://bijux.io/bijux-canon/06-bijux-canon-runtime/architecture/execution-model/) when you need the plan-to-replay
  path rather than a directory listing
- open [State and Persistence](https://bijux.io/bijux-canon/06-bijux-canon-runtime/architecture/state-and-persistence/) when the real question
  is what becomes durable and where it is stored
- open [Integration Seams](https://bijux.io/bijux-canon/06-bijux-canon-runtime/architecture/integration-seams/) before broadening runtime's
  dependencies on lower packages or outside systems

## Pages In This Section

- [Module Map](https://bijux.io/bijux-canon/06-bijux-canon-runtime/architecture/module-map/)
- [Dependency Direction](https://bijux.io/bijux-canon/06-bijux-canon-runtime/architecture/dependency-direction/)
- [Execution Model](https://bijux.io/bijux-canon/06-bijux-canon-runtime/architecture/execution-model/)
- [State and Persistence](https://bijux.io/bijux-canon/06-bijux-canon-runtime/architecture/state-and-persistence/)
- [Integration Seams](https://bijux.io/bijux-canon/06-bijux-canon-runtime/architecture/integration-seams/)
- [Error Model](https://bijux.io/bijux-canon/06-bijux-canon-runtime/architecture/error-model/)
- [Extensibility Model](https://bijux.io/bijux-canon/06-bijux-canon-runtime/architecture/extensibility-model/)
- [Code Navigation](https://bijux.io/bijux-canon/06-bijux-canon-runtime/architecture/code-navigation/)
- [Architecture Risks](https://bijux.io/bijux-canon/06-bijux-canon-runtime/architecture/architecture-risks/)

## Open This Section When

- you are tracing structure, execution flow, or dependency pressure
- you need to understand how modules fit before refactoring
- you are reviewing design drift rather than one isolated bug

## Open Another Section When

- the real question is why runtime should own a behavior at all
- you need CLI, API, schema, or artifact contract detail more than module
  layout
- you are deciding whether the proof surface is strong enough rather than how
  the design is shaped

## Concrete Anchors

- `src/bijux_canon_runtime/application/` for planning, replay support, and
  execution authority
- `src/bijux_canon_runtime/runtime/execution/` for the governed lifecycle
- `src/bijux_canon_runtime/observability/storage/` and `analysis/` for durable
  recording and replay inspection
- `src/bijux_canon_runtime/model/` and `contracts/` for the structural
  language the rest of the package must obey

## Across This Package

- open [Foundation](https://bijux.io/bijux-canon/06-bijux-canon-runtime/foundation/) when a structural issue is really a
  boundary issue
- open [Interfaces](https://bijux.io/bijux-canon/06-bijux-canon-runtime/interfaces/) when architecture reaches a public
  CLI, API, schema, or artifact seam
- open [Quality](https://bijux.io/bijux-canon/06-bijux-canon-runtime/quality/) when the question becomes whether the
  structure is adequately defended by tests and invariants

## Bottom Line

Open this section to decide whether a structural change makes runtime easier
or harder to explain in terms of planning, governed execution, durable state,
and replay analysis. If the change works only because the design becomes harder
to read, redesign is safer than acceptance.

