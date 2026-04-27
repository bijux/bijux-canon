---
title: Code Navigation
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-04-26
---

# Code Navigation

Code navigation should shorten the path from a agent orchestration question to the owning files in `bijux-canon-agent`. If readers still need exploratory digging, the navigation story is not specific enough.

## What To Check

- start with `src/bijux_canon_agent` and tracked workflow surfaces for the main ownership seam
- follow with `tests` for determinism and traceability evidence when the question is whether the code still matches the structure
- treat wide, unfocused navigation advice as a sign that the structure is not yet legible enough

## First Proof Check

- `src/bijux_canon_agent` and tracked workflow surfaces for the structural ownership boundary
- `tests` for determinism and traceability evidence for executable confirmation that the structure still holds

## Bottom Line

If `bijux-canon-agent` needs hidden structure to defend role coordination, workflow order, and traces, the architecture is already too opaque.
