---
title: State and Persistence
audience: mixed
type: guide
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-04-04
---

# State and Persistence

State in `bijux-canon-agent` should be explicit enough that a maintainer can say what is
transient, what is serialized, and what neighboring packages must not assume.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-agent"] --> section["Architecture"]
    section --> page["State and Persistence"]
    dest1["reviewable boundaries"]
    dest2["operator clarity"]
    dest3["change safety"]
    page --> dest1
    page --> dest2
    page --> dest3
```

```mermaid
flowchart TD
    page["State and Persistence"]
    focus1["Owned package surface"]
    page --> focus1
    focus1_1["agent role implementations and role-specific helpers"]
    focus1 --> focus1_1
    focus1_2["deterministic orchestration of the local agent pipeline"]
    focus1 --> focus1_2
    focus2["Evidence to inspect"]
    page --> focus2
    focus2_1["src/bijux_canon_agent/agents"]
    focus2 --> focus2_1
    focus2_2["trace-backed final outputs"]
    focus2 --> focus2_2
    focus3["Review pressure"]
    page --> focus3
    focus3_1["Architecture"]
    focus3 --> focus3_1
    focus3_2["tests/unit for local behavior and utility coverage"]
    focus3 --> focus3_2
```

## Durable Surfaces

- trace-backed final outputs
- workflow graph execution records
- operator-visible result artifacts

## Code Areas to Inspect

- `src/bijux_canon_agent/agents` for role-local behavior
- `src/bijux_canon_agent/pipeline` for execution flow orchestration
- `src/bijux_canon_agent/application` for workflow policy and graph logic
- `src/bijux_canon_agent/llm` for LLM runtime integration support
- `src/bijux_canon_agent/interfaces` for CLI boundaries and operator helpers
- `src/bijux_canon_agent/traces` for trace-facing models and persistence helpers

## Use This Page When

- you are tracing internal structure or execution flow
- you need to understand where modules fit before refactoring
- you are reviewing architectural drift instead of one local bug

## What This Page Answers

- how bijux-canon-agent is structured internally
- which modules control the main execution path
- where architectural drift would become visible first

## Reviewer Lens

- trace the claimed execution path through the listed modules
- look for dependency direction that now contradicts the documented seam
- verify that architectural risks still match the current code structure

## Honesty Boundary

This page describes the current structural model of bijux-canon-agent, but it does not by itself prove that every import or runtime path still obeys that model.

## Purpose

This page marks the package's state and artifact boundary.

## Stability

Keep it aligned with the actual artifact shapes and serialized outputs.
