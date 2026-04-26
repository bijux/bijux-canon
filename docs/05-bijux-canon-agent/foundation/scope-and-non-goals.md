---
title: Scope and Non-Goals
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-04-26
---

# Scope and Non-Goals

The scope of `bijux-canon-agent` is coordination that stays inspectable. It is not a general layer for all late-stage behavior in the system.

## In Scope

- deterministic workflow progression across agent roles and steps
- trace-producing orchestration surfaces that explain what happened
- agent-facing contracts that callers and neighboring packages can inspect

## Non-Goals

- retrieval or reasoning semantics inside lower packages
- final authority over persistence, replay acceptance, or governed runs
- repository-wide maintainer automation and release mechanics

## Scope Check

If the change makes workflows harder to reconstruct from traces, the package is getting more magical instead of more useful.

## Bottom Line

A package boundary earns trust partly by the work it refuses to absorb. `bijux-canon-agent` should stay narrow enough that its role can still be explained in one pass.
