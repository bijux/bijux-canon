---
title: Change Management
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-26
---

# Change Management

The repository should make change easier to reason about, not easier to hide.

## Fail-Fast Gates

A cross-package change is not ready to merge until it passes all of these tests:

- the owner of each changed behavior is still easy to name
- docs, proof, and implementation move in the same change series when they
  describe the same rule
- release-facing or compatibility effects are visible in the changed surfaces
- the commit boundaries explain durable intent instead of bundling unrelated work

## Most Common Failure Mode

The usual repository rework debt comes from changes that technically worked but
left the reason for the split harder to explain. The cost appears later as
cleanup, duplicated rules, or confused root ownership.

## First Proof Checks

- the changed handbook pages under `docs/`
- the package or root surface that implements the behavior
- the test, workflow, or schema check that proves the rule still holds

## Bottom Line

Good change management closes the explanation loop while the change is still in
flight. If private memory is needed to explain why the batch exists, it is not
yet packaged well enough for durable history.
