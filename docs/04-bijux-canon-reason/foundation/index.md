---
title: Foundation
audience: mixed
type: index
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-04-26
---

# Foundation

Open this section when you need the durable answer to a simple question: why
does `bijux-canon-reason` exist as its own package between retrieval below and
agent or runtime control above?

This package is where evidence stops being only retrievable and starts becoming
arguable. It owns planning, claim formation, verification, and the traceable
artifacts that let a reviewer inspect what the reasoning layer concluded and
why.

## Start Here

- open [Package Overview](https://bijux.io/bijux-canon/04-bijux-canon-reason/foundation/package-overview/) for the shortest description of
  the package role
- open [Ownership Boundary](https://bijux.io/bijux-canon/04-bijux-canon-reason/foundation/ownership-boundary/) when the question is whether
  logic belongs in retrieval, reasoning, agent orchestration, or runtime
- open [Lifecycle Overview](https://bijux.io/bijux-canon/04-bijux-canon-reason/foundation/lifecycle-overview/) when you need the
  end-to-end shape from evidence intake to verified reasoning output

## Pages In This Section

- [Package Overview](https://bijux.io/bijux-canon/04-bijux-canon-reason/foundation/package-overview/)
- [Scope and Non-Goals](https://bijux.io/bijux-canon/04-bijux-canon-reason/foundation/scope-and-non-goals/)
- [Ownership Boundary](https://bijux.io/bijux-canon/04-bijux-canon-reason/foundation/ownership-boundary/)
- [Repository Fit](https://bijux.io/bijux-canon/04-bijux-canon-reason/foundation/repository-fit/)
- [Capability Map](https://bijux.io/bijux-canon/04-bijux-canon-reason/foundation/capability-map/)
- [Domain Language](https://bijux.io/bijux-canon/04-bijux-canon-reason/foundation/domain-language/)
- [Lifecycle Overview](https://bijux.io/bijux-canon/04-bijux-canon-reason/foundation/lifecycle-overview/)
- [Dependencies and Adjacencies](https://bijux.io/bijux-canon/04-bijux-canon-reason/foundation/dependencies-and-adjacencies/)
- [Change Principles](https://bijux.io/bijux-canon/04-bijux-canon-reason/foundation/change-principles/)

## Open This Section When

- you need the package role before looking at modules, commands, or tests
- you are checking whether a behavior is really reasoning rather than retrieval,
  orchestration, or runtime governance
- a reader needs one page that explains why this package exists without reading
  the whole tree

## Open Another Section When

- the real question is where a module lives or how control flows through code
- you are deciding whether a CLI, API, schema, or artifact is a supported
  contract
- the main concern is operating the package or proving a change is safe

## Across This Package

- open [Architecture](https://bijux.io/bijux-canon/04-bijux-canon-reason/architecture/) for module boundaries,
  execution flow, and persistence seams
- open [Interfaces](https://bijux.io/bijux-canon/04-bijux-canon-reason/interfaces/) for CLI, API, trace, and schema
  contracts
- open [Operations](https://bijux.io/bijux-canon/04-bijux-canon-reason/operations/) for install, replay, diagnostics,
  and release procedures
- open [Quality](https://bijux.io/bijux-canon/04-bijux-canon-reason/quality/) for proof surfaces, invariants, and known
  limitations

## Concrete Anchors

- `packages/bijux-canon-reason` as the package root
- `packages/bijux-canon-reason/src/bijux_canon_reason` as the import boundary
- `packages/bijux-canon-reason/tests` as the package proof surface

## Bottom Line

`Foundation` leaves leave no doubt about the package boundary: retrieval finds
evidence, reasoning turns it into inspectable claims and checks, agent
coordinates multi-step work, and runtime decides what becomes durable and
acceptable.

