---
title: Security Gates
audience: mixed
type: guide
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-04
---

# Security Gates

Security checks that are about repository health rather than product behavior
live in `bijux-canon-dev`.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon"] --> section["Maintainer Handbook"]
    section --> page["Security Gates"]
    dest1["quality gates"]
    dest2["schema governance"]
    dest3["release support"]
    page --> dest1
    page --> dest2
    page --> dest3
```

## Current Security Surfaces

- `security/pip_audit_gate.py`
- package tests that confirm expected security tooling behavior
- CI integration through root workflows

## Purpose

This page marks the boundary between maintenance security tooling and product runtime security behavior.

## Stability

Keep it aligned with the actual checks we can execute and verify.
