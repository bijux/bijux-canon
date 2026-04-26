---
title: Capability Map
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-04-26
---

# Capability Map

The capability map for `bijux-canon-agent` should let a reviewer connect workflow promises to the code that coordinates roles and emits traces. If orchestration behavior cannot be mapped clearly, the package starts to look magical.

## Capability To Code

- `application/` and orchestration flows own role sequencing and workflow coordination
- agent services and role modules own the behavior of local actors inside a workflow
- `interfaces/` and artifacts own the surfaces where callers and operators inspect workflow behavior

## Visible Outputs

- trace-bearing workflow execution records
- role-specific outputs that remain attributable to a step and an order
- agent-facing contracts that expose orchestration intentionally

## Bottom Line

A capability is only real when a reviewer can trace it to code, tests, and outputs without guessing.
