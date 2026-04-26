---
title: Extensibility Model
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-04-26
---

# Extensibility Model

Extensibility only helps when it preserves the core package argument. In `bijux-canon-agent`, extension points should widen role coordination, workflow order, and traces intentionally rather than invite neighboring concerns in through convenience hooks.

## What To Check

- name the extension points that are safe because they preserve the package role
- name the boundaries that extensions must not cross
- prefer extension seams that keep review pressure visible in code and tests

## First Proof Check

- `src/bijux_canon_agent` and tracked workflow surfaces for the structural ownership boundary
- `tests` for determinism and traceability evidence for executable confirmation that the structure still holds

## Bottom Line

If `bijux-canon-agent` needs hidden structure to defend role coordination, workflow order, and traces, the architecture is already too opaque.
