---
title: Capability Map
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-04-26
---

# Capability Map

The capability map for `bijux-canon-reason` should let a reviewer tie reasoning claims to the code that forms, checks, and records them. If the package promise cannot be mapped to named reasoning areas, auditability is already slipping.

## Capability To Code

- `application/` and reasoning workflows own how evaluation steps are coordinated inside the package boundary
- `domain/` and reasoning services own claim formation, verification, and provenance-aware reasoning behavior
- `interfaces/` and package artifacts own the surfaces where reasoning leaves the package as something reviewable

## Visible Outputs

- claims and checks tied to retrieved evidence
- provenance-rich reasoning artifacts
- reviewable package outputs that agent and runtime can consume

## Bottom Line

A capability is only real when a reviewer can trace it to code, tests, and outputs without guessing.
