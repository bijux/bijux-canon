---
title: Release Policy
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-26
---

# Release Policy

Compatibility packages should release only when they still protect a real
migration need or when the canonical target changes in a way that requires the
bridge metadata to move with it. A compatibility release should feel justified,
narrow, and temporary.

## Release Rules

- release a compatibility package only when continuity still protects a real
  dependent environment
- keep the package thin and aligned with the canonical target
- avoid feature growth or product-like change history in the compatibility layer

## Warning Signs

- releases happen automatically with no remaining documented dependent use
- compatibility release notes read like feature delivery instead of bridge
  maintenance
- the legacy package starts behaving like a peer of the canonical package

## First Proof Check

- `packages/compat-*`
- compatibility package metadata and README files
- release workflow inputs and published artifacts
