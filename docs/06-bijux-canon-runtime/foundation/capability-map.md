---
title: Capability Map
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-26
---

# Capability Map

The capability map for `bijux-canon-runtime` should let a reviewer tie authority claims to the code that accepts, persists, replays, and governs runs. If authority cannot be mapped clearly, the package is relying on convention instead of policy.

## Capability To Code

- `application/` owns execution authority entrypoints and governed run flow
- `model/` and runtime services own acceptance, verification, and persistence rules
- `observability/` and interfaces own the durable artifacts and surfaces that make replay possible

## Visible Outputs

- governed run records
- persistent traces and replay artifacts
- runtime-facing contracts that define what a durable run means

## Bottom Line

A capability is only real when a reviewer can trace it to code, tests, and outputs without guessing.
