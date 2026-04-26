---
title: Scope and Non-Goals
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-04-26
---

# Scope and Non-Goals

The scope of `bijux-canon-reason` is to make conclusions inspectable. It is not a fallback place for any logic that feels “smart.”

## In Scope

- turning retrieved evidence into claims, checks, and reasoning artifacts
- reasoning-side provenance and verification behavior
- package-local interfaces that expose reasoning outputs as intentional surfaces

## Non-Goals

- search execution and retrieval replay behavior
- role coordination across multi-step agent workflows
- runtime persistence, acceptance, or governed replay authority

## Scope Check

If the change adds cleverness without making claims easier to inspect or verify, it is probably not reasoning ownership.

## Bottom Line

A package boundary earns trust partly by the work it refuses to absorb. `bijux-canon-reason` should stay narrow enough that its role can still be explained in one pass.
