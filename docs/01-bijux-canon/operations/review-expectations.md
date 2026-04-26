---
title: Review Expectations
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-09
---

# Review Expectations

Repository review should be sharper at the root than it is in purely local code.

The reason is simple: root changes alter how the whole package family is built,
read, verified, or released. That means a “small” root edit can carry wider
consequences than a larger package-local edit. Review expectations make that
pressure visible.

## Root Review Expectations

- confirm the owning repository surface is still the right one for the change
- check that docs, automation, and proof assets move together when they describe
  one repository rule
- verify that the change does not smuggle product behavior into maintainer or
  root automation layers
- prefer clear, durable commit intent over vague historical shorthand

## Evidence To Check

- the relevant handbook page under `docs/`
- the root or package automation file that implements the behavior
- the test or workflow that proves the rule still holds

## Red Flags

- the explanation is spread across multiple places but none of them clearly own
  it
- the change is easy to apply but hard to describe at the repository boundary
- review confidence depends on memory instead of checked-in proof

