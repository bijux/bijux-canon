---
title: Foundation
audience: mixed
type: index
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-04-26
---

# Foundation

Open this section when you need the durable answer to a simple question: why
does `bijux-canon-agent` exist between reasoning outputs below and runtime
authority above?

This package is where one reasoning-capable step becomes coordinated work. It
owns role-based agents, pipeline control, trace-bearing execution flow, and the
rules that keep orchestration inspectable instead of magical.

## Start Here

- open [Package Overview](https://bijux.io/bijux-canon/05-bijux-canon-agent/foundation/package-overview/) for the shortest explanation of
  the orchestration role
- open [Ownership Boundary](https://bijux.io/bijux-canon/05-bijux-canon-agent/foundation/ownership-boundary/) when the question is whether
  behavior belongs in reasoning, agent coordination, or runtime governance
- open [Lifecycle Overview](https://bijux.io/bijux-canon/05-bijux-canon-agent/foundation/lifecycle-overview/) when you need the package
  story from agent input through traceable output

## Pages In This Section

- [Package Overview](https://bijux.io/bijux-canon/05-bijux-canon-agent/foundation/package-overview/)
- [Scope and Non-Goals](https://bijux.io/bijux-canon/05-bijux-canon-agent/foundation/scope-and-non-goals/)
- [Ownership Boundary](https://bijux.io/bijux-canon/05-bijux-canon-agent/foundation/ownership-boundary/)
- [Repository Fit](https://bijux.io/bijux-canon/05-bijux-canon-agent/foundation/repository-fit/)
- [Capability Map](https://bijux.io/bijux-canon/05-bijux-canon-agent/foundation/capability-map/)
- [Domain Language](https://bijux.io/bijux-canon/05-bijux-canon-agent/foundation/domain-language/)
- [Lifecycle Overview](https://bijux.io/bijux-canon/05-bijux-canon-agent/foundation/lifecycle-overview/)
- [Dependencies and Adjacencies](https://bijux.io/bijux-canon/05-bijux-canon-agent/foundation/dependencies-and-adjacencies/)
- [Change Principles](https://bijux.io/bijux-canon/05-bijux-canon-agent/foundation/change-principles/)

## Open This Section When

- you need the package role before looking at APIs, modules, or workflows
- you are deciding whether a feature is orchestration behavior or belongs in a
  lower or higher package
- a reader needs one page that explains why this package exists without reading
  the whole handbook

## Open Another Section When

- the main question is where a module or execution path lives
- you are deciding whether a CLI, API, artifact, or import is a contract
- the issue is procedural or proof-oriented rather than boundary-oriented

## Across This Package

- open [Architecture](https://bijux.io/bijux-canon/05-bijux-canon-agent/architecture/) for module groups, execution
  flow, and dependency direction
- open [Interfaces](https://bijux.io/bijux-canon/05-bijux-canon-agent/interfaces/) for CLI, API, artifact, and import
  contracts
- open [Operations](https://bijux.io/bijux-canon/05-bijux-canon-agent/operations/) for setup, diagnostics, and release
  procedures
- open [Quality](https://bijux.io/bijux-canon/05-bijux-canon-agent/quality/) for trust posture, invariants, and review
  standards

## Concrete Anchors

- `packages/bijux-canon-agent` as the package root
- `packages/bijux-canon-agent/src/bijux_canon_agent` as the import boundary
- `packages/bijux-canon-agent/tests` as the package proof surface

## Bottom Line

`Foundation` should leave no doubt about the package boundary: reasoning
produces inspectable content, agent coordination turns that into role-based and
trace-backed workflow behavior, and runtime decides what becomes governed and
durable.

