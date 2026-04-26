---
title: Scope and Non-Goals
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-26
---

# Scope and Non-Goals

The scope of `bijux-canon-runtime` is explicit authority over runs. It is not a convenient place for any code that happens late in execution.

## In Scope

- acceptance policy for governed runs
- persistence and replay behavior tied to runtime authority
- runtime-facing interfaces and artifacts that define what a durable run means

## Non-Goals

- package-local semantics owned by ingest, index, reason, or agent
- maintainer automation that belongs to the maintenance handbook
- convenience features that never affect governed run outcomes

## Scope Check

If the change makes runtime broader without making run authority easier to explain, it is probably misplaced.

## Bottom Line

A package boundary earns trust partly by the work it refuses to absorb. `bijux-canon-runtime` should stay narrow enough that its role can still be explained in one pass.
