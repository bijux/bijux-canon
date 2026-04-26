---
title: Retirement Playbook
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-09
---

# Retirement Playbook

Compatibility packages should leave the repository by a visible process, not by
wishful thinking or by surprise.

This playbook exists so retirement becomes a planned conclusion to a migration
story. It should help maintainers separate “we hope nobody needs this anymore”
from “we have enough evidence to remove it without stranding supported users.”

## Retirement Steps

- confirm the supported environments that still depend on the legacy name
- make sure the canonical target and migration docs have been stable long
  enough to be credible
- verify that package metadata, docs, and release notes all communicate the
  retirement clearly
- remove the package only when the remaining dependency is understood rather
  than guessed

## Evidence To Gather

- usage or support evidence for the remaining legacy name
- migration guidance that has already been published and maintained
- validation that no supported automation still depends on the legacy package

