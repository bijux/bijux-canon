---
title: Review Expectations
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-26
---

# Review Expectations

Repository review should be sharper at the root than it is in purely local
code.

## Root Review Gates

Before accepting a root-facing change, confirm that:

- the chosen repository surface is still the right owner
- docs, automation, and proof assets move together when they describe one rule
- the change does not smuggle product behavior into maintainer or root layers
- the commit intent is durable enough to understand years later without private memory

## Evidence To Check First

- the relevant handbook page under `docs/`
- the root or package automation file that implements the behavior
- the test, workflow, or schema surface that proves the rule still holds

## Red Flags

- the explanation is spread across multiple places but none clearly own it
- the change is easy to apply but hard to describe at the repository boundary
- review confidence depends on memory instead of checked-in proof

## Bottom Line

Root review is stricter because root mistakes spread farther. If the owner,
proof, or change intent is still fuzzy, the work is not ready.
