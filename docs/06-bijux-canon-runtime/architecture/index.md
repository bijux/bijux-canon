---
title: Architecture
audience: mixed
type: index
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-26
---

# Architecture

Open this section when the question is structural: where run authority lives, how acceptance and persistence flow through the package, and how runtime stays narrower than “whatever happens last.”

## Read These First

- open [Module Map](https://bijux.io/bijux-canon/06-bijux-canon-runtime/architecture/module-map/) first when you need the owning code area for a runtime authority concern
- open [Execution Model](https://bijux.io/bijux-canon/06-bijux-canon-runtime/architecture/execution-model/) when you need the real path from lower-package output to governed run artifact
- open [Integration Seams](https://bijux.io/bijux-canon/06-bijux-canon-runtime/architecture/integration-seams/) when a change could blur lower-package semantics with final authority

## Structural Risk

The main architectural risk here is broadening runtime until execution order replaces explicit authority design.

## First Proof Check

- `src/bijux_canon_runtime/application/execute_flow.py` for authority entrypoints
- `src/bijux_canon_runtime/observability` for replay and durable traces
- `tests` for acceptance, replay, and persistence evidence


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

## Leave This Section When

- leave for [Interfaces](https://bijux.io/bijux-canon/06-bijux-canon-runtime/interfaces/) when the structural question is already a public contract question
- leave for [Operations](https://bijux.io/bijux-canon/06-bijux-canon-runtime/operations/) when the issue is running, diagnosing, or releasing the package rather than explaining its shape
- leave for [Quality](https://bijux.io/bijux-canon/06-bijux-canon-runtime/quality/) when the structure is clear and the real question is whether the package has proved it strongly enough

## Bottom Line

A structure that cannot be explained in one pass is already carrying too much hidden policy.
