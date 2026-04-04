---
title: Capability Map
audience: mixed
type: guide
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-04-04
---

# Capability Map

The package capabilities can be read as a map from modules to behavior.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-reason"] --> section["Foundation"]
    section --> page["Capability Map"]
    dest1["reviewable boundaries"]
    dest2["operator clarity"]
    dest3["change safety"]
    page --> dest1
    page --> dest2
    page --> dest3
```

```mermaid
flowchart TD
    page["Capability Map"]
    focus1["Owned package surface"]
    page --> focus1
    focus1_1["reasoning plans, claims, and evidence-aware reasoning models"]
    focus1 --> focus1_1
    focus1_2["execution of reasoning steps and local tool dispatch"]
    focus1 --> focus1_2
    focus2["Evidence to inspect"]
    page --> focus2
    focus2_1["src/bijux_canon_reason/planning"]
    focus2 --> focus2_1
    focus2_2["reasoning traces and replay diffs"]
    focus2 --> focus2_2
    focus3["Review pressure"]
    page --> focus3
    focus3_1["Foundation"]
    focus3 --> focus3_1
    focus3_2["tests/unit for planning, reasoning, execution, verification, and interfaces"]
    focus3 --> focus3_2
```

## Capability Map

- `src/bijux_canon_reason/planning` for plan construction and intermediate representation
- `src/bijux_canon_reason/reasoning` for claim and reasoning semantics
- `src/bijux_canon_reason/execution` for step execution and tool dispatch
- `src/bijux_canon_reason/verification` for checks and validation outcomes
- `src/bijux_canon_reason/traces` for trace replay and diff support
- `src/bijux_canon_reason/interfaces` for CLI and serialization boundaries

## Produced Artifacts

- reasoning traces and replay diffs
- claim and verification outcomes
- evaluation suite artifacts

## What This Page Answers

- what bijux-canon-reason is expected to own
- what remains outside the package boundary
- which neighboring seams a reviewer should compare next

## Purpose

This page helps a reader quickly map package claims to code areas.

## Stability

Keep it aligned with the real package modules and generated outputs.
