---
title: Foundation
audience: mixed
type: index
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-26
---

# Foundation

Open this section to understand why `bijux-canon-runtime` exists, what it owns
on purpose, and where its boundary stops.

Read this section first when you need the durable package story before code
detail. A quick skim makes the role, the boundary, and the neighboring
seams legible.

`bijux-canon-runtime` exists so execution can be judged, persisted, and
replayed under explicit policy instead of by convention. If the package still
feels blurry after this section, the authority story is not clear enough yet.

## Visual Summary

```mermaid
flowchart LR
    reader["reader question<br/>why does runtime have authority at all?"]
    boundary["authority boundary<br/>what belongs here"]
    lifecycle["run lifecycle<br/>prepare, execute, persist, replay"]
    artifacts["durable traces, envelopes, and stores"]
    neighbors["lower packages execute work<br/>runtime judges it"]
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    class reader page;
    class boundary,lifecycle,artifacts positive;
    class neighbors caution;
    reader --> boundary
    boundary --> lifecycle
    lifecycle --> artifacts
    boundary --> neighbors
```

## Start Here

- open [Package Overview](https://bijux.io/bijux-canon/06-bijux-canon-runtime/foundation/package-overview/) for the shortest durable
  statement of the runtime role
- open [Ownership Boundary](https://bijux.io/bijux-canon/06-bijux-canon-runtime/foundation/ownership-boundary/) when the real question is
  whether a behavior belongs in runtime or in a lower package
- open [Lifecycle Overview](https://bijux.io/bijux-canon/06-bijux-canon-runtime/foundation/lifecycle-overview/) when you need the governed
  run path before reading modules or schemas
- open [Dependencies and Adjacencies](https://bijux.io/bijux-canon/06-bijux-canon-runtime/foundation/dependencies-and-adjacencies/) before
  broadening the package into a neighbor's responsibility

## Pages In This Section

- [Package Overview](https://bijux.io/bijux-canon/06-bijux-canon-runtime/foundation/package-overview/)
- [Scope and Non-Goals](https://bijux.io/bijux-canon/06-bijux-canon-runtime/foundation/scope-and-non-goals/)
- [Ownership Boundary](https://bijux.io/bijux-canon/06-bijux-canon-runtime/foundation/ownership-boundary/)
- [Repository Fit](https://bijux.io/bijux-canon/06-bijux-canon-runtime/foundation/repository-fit/)
- [Capability Map](https://bijux.io/bijux-canon/06-bijux-canon-runtime/foundation/capability-map/)
- [Domain Language](https://bijux.io/bijux-canon/06-bijux-canon-runtime/foundation/domain-language/)
- [Lifecycle Overview](https://bijux.io/bijux-canon/06-bijux-canon-runtime/foundation/lifecycle-overview/)
- [Dependencies and Adjacencies](https://bijux.io/bijux-canon/06-bijux-canon-runtime/foundation/dependencies-and-adjacencies/)
- [Change Principles](https://bijux.io/bijux-canon/06-bijux-canon-runtime/foundation/change-principles/)

## Open Foundation When

- you need the package idea before the implementation detail
- you are deciding whether work belongs here or in a neighboring package
- you want the shortest honest explanation of what this package is for

## Open Another Section When

- the real question is already about module layout, execution flow, or store
  structure
- you need CLI, API, schema, or artifact contract detail more than boundary
  logic
- you are evaluating proof quality rather than package role

## Concrete Anchors

- `src/bijux_canon_runtime/application/execute_flow.py` for runtime-owned
  authority entrypoints
- `src/bijux_canon_runtime/model/execution/` and `model/verification/` for the
  domain language of acceptable runs
- `src/bijux_canon_runtime/observability/` for the durable replay and trace
  surfaces that make runtime distinct
- `tests/unit/runtime/` and `tests/regression/` for the proof surface that this
  boundary still holds under drift pressure

## Read Across The Package

- open [Architecture](https://bijux.io/bijux-canon/06-bijux-canon-runtime/architecture/) when the question becomes how
  authority is implemented rather than why it exists
- open [Interfaces](https://bijux.io/bijux-canon/06-bijux-canon-runtime/interfaces/) when the runtime role reaches a
  CLI, API, schema, or durable artifact contract
- open [Quality](https://bijux.io/bijux-canon/06-bijux-canon-runtime/quality/) when the real question is whether runtime
  has proven that authority strongly enough

## Bottom Line

Open `Foundation` to decide whether a change makes runtime easier or harder to
defend as the authority layer in the system. If the work makes the package
broader without making that authority role clearer, stop and re-check the
boundary before treating it as a local improvement.

