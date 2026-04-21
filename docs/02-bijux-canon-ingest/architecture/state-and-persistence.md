---
title: State and Persistence
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-04-04
---

# State and Persistence

State in `bijux-canon-ingest` should be explicit enough that a maintainer can say what is
transient, what is serialized, and what neighboring packages must not assume.

That clarity matters because state tends to spread silently when it is not named.
Once readers stop knowing which outputs are durable and which values are local,
interface and operations pages quickly become less trustworthy.

Treat the architecture pages for `bijux-canon-ingest` as a reviewer-facing map of structure and flow. They should shorten code reading, not try to replace it.

## Visual Summary

```mermaid
graph TD
    A[State and Persistence] --> B[Input state]
    B --> C[Transient processing state]
    C --> D[Materialized artifacts]
    D --> E[Persistent references]
    E --> F[Replayable ingest state]
```

## Durable Surfaces

- normalized document trees
- chunk collections and retrieval-ready records
- diagnostic output produced during ingest workflows

## Code Areas to Inspect

- `src/bijux_canon_ingest/processing` for deterministic document transforms
- `src/bijux_canon_ingest/retrieval` for retrieval-oriented models and assembly
- `src/bijux_canon_ingest/application` for package workflows
- `src/bijux_canon_ingest/infra` for local adapters and infrastructure helpers
- `src/bijux_canon_ingest/interfaces` for CLI and HTTP boundaries
- `src/bijux_canon_ingest/safeguards` for protective rules for ingest behavior

## Concrete Anchors

- `src/bijux_canon_ingest/processing` for deterministic document transforms
- `src/bijux_canon_ingest/retrieval` for retrieval-oriented models and assembly
- `src/bijux_canon_ingest/application` for package workflows

## Use This Page When

- you are tracing structure, execution flow, or dependency pressure
- you need to understand how modules fit before refactoring
- you are reviewing design drift rather than one isolated bug

## Decision Rule

Use `State and Persistence` to decide whether a structural change makes `bijux-canon-ingest` easier or harder to explain in terms of modules, dependency direction, and execution flow. If the change works only because the design becomes harder to read, the safer answer is redesign rather than acceptance.

## What This Page Answers

- how `bijux-canon-ingest` is organized internally in terms a reviewer can follow
- which modules carry the main execution and dependency story
- where structural drift would show up before it becomes expensive

## Reviewer Lens

- trace the described execution path through the named modules instead of trusting the diagram alone
- look for dependency direction or layering that now contradicts the documented seam
- verify that the structural risks named here still match the current code shape

## Honesty Boundary

This page describes the current structural model of `bijux-canon-ingest`, but it does not guarantee that every import path or runtime path still obeys that model. Readers should treat it as a map that must stay aligned with code and tests, not as an authority above them.

## Next Checks

- move to interfaces when the review reaches a public or operator-facing seam
- move to operations when the concern becomes repeatable runtime behavior
- move to quality when you need proof that the documented structure is still protected

## Purpose

This page marks the package's state and artifact boundary.

## Stability

Keep it aligned with the actual artifact shapes and serialized outputs.
