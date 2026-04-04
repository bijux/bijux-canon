---
title: Local Development
audience: mixed
type: guide
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-04-04
---

# Local Development

Local development should happen inside `packages/bijux-canon-agent` with tests and docs updated
in the same change series as the code.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-agent"] --> section["Operations"]
    section --> page["Local Development"]
    dest1["reviewable boundaries"]
    dest2["operator clarity"]
    dest3["change safety"]
    page --> dest1
    page --> dest2
    page --> dest3
```

## Development Anchors

- tests/unit for local behavior and utility coverage
- tests/integration and tests/e2e for end-to-end workflow behavior
- tests/invariants for package promises that should not drift
- tests/api for HTTP-facing validation

## Purpose

This page records the package-local development posture.

## Stability

Keep it aligned with the actual test layout and maintenance workflow.
