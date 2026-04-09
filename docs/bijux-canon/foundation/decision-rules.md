---
title: Decision Rules
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-09
---

# Decision Rules

The root should make decisions easier, not more political.

This page turns the repository philosophy into a small set of routing rules. A
reader should be able to use these rules when a change proposal feels plausible
in more than one location. They are not substitutes for judgment, but they keep
judgment anchored to repository intent rather than to whoever touched the area
most recently.

## Routing Rules

- if one package can explain the behavior honestly, start in that package
- if the question is about shared documentation shape, schema storage, or
  workflow coordination, start at the root
- if the issue is about repository health tooling, start in the maintenance
  handbook and `bijux-canon-dev`
- if the issue exists only because of a legacy public name, start in the
  compatibility handbook

## Escalate To Root When

- more than one canonical package contract would otherwise need the same rule
- a workflow or schema check is protecting repository-wide truth rather than a
  local behavior
- the docs structure itself is part of the problem being solved

## Send Work Back Down When

- the root page starts explaining package-local implementation detail
- a maintainer script begins to encode product behavior
- compatibility logic is treated as if it were the preferred package surface

## Purpose

This page gives maintainers durable decision rules for routing work to the
right repository layer.

## Stability

Keep these rules aligned with how authority is actually divided across the
repository.
