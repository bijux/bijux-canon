---
title: Retirement Conditions
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-26
---

# Retirement Conditions

A compatibility package is ready to retire only when the supported
environments that still need it are known and the exit path is documented.
Retirement should be driven by evidence, not by vague anxiety or cosmetic
cleanup pressure.

## Required Signals

- no supported consumer still depends on the legacy distribution, import, or
  command name
- canonical package docs and migration guidance have been stable long enough to
  support the transition
- repository searches, package metadata, and release checks no longer show
  hidden dependence on the legacy name

## If Evidence Is Missing

Keep the bridge temporarily and close the evidence gap. A bridge should not be
removed on optimism alone.

## First Proof Check

- repository-wide search for legacy names
- compatibility package metadata and README files
- release and validation records that show the bridge is no longer needed
