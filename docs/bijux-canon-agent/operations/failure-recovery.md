---
title: Failure Recovery
audience: mixed
type: guide
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-04-04
---

# Failure Recovery

Failure recovery starts with knowing which artifacts, interfaces, and tests expose the problem.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-agent"] --> section["Operations"]
    section --> page["Failure Recovery"]
    dest1["reviewable boundaries"]
    dest2["operator clarity"]
    dest3["change safety"]
    page --> dest1
    page --> dest2
    page --> dest3
```

## Recovery Anchors

- interface surfaces: CLI entrypoint in src/bijux_canon_agent/interfaces/cli/entrypoint.py, operator configuration under src/bijux_canon_agent/config, HTTP-adjacent modules under src/bijux_canon_agent/api
- artifacts to inspect: trace-backed final outputs, workflow graph execution records, operator-visible result artifacts
- tests to run: tests/unit for local behavior and utility coverage, tests/integration and tests/e2e for end-to-end workflow behavior

## Purpose

This page gives maintainers a durable frame for triaging package failures.

## Stability

Keep it aligned with the package entrypoints and diagnostic outputs.
