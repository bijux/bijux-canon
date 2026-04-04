---
title: State and Persistence
audience: mixed
type: guide
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-04-04
---

# State and Persistence

State in `bijux-canon-reason` should be explicit enough that a maintainer can say what is
transient, what is serialized, and what neighboring packages must not assume.

## Durable Surfaces

- reasoning traces and replay diffs
- claim and verification outcomes
- evaluation suite artifacts

## Code Areas to Inspect

- `src/bijux_canon_reason/planning` for plan construction and intermediate representation
- `src/bijux_canon_reason/reasoning` for claim and reasoning semantics
- `src/bijux_canon_reason/execution` for step execution and tool dispatch
- `src/bijux_canon_reason/verification` for checks and validation outcomes
- `src/bijux_canon_reason/traces` for trace replay and diff support
- `src/bijux_canon_reason/interfaces` for CLI and serialization boundaries

## Purpose

This page marks the package's state and artifact boundary.

## Stability

Keep it aligned with the actual artifact shapes and serialized outputs.
