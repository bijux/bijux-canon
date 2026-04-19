---
title: Dependency Continuity
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-09
---

# Dependency Continuity

Compatibility packages are successful only when they preserve continuity while
still encouraging forward motion.

The main continuity promise in this repository is narrow: a legacy package can
keep an environment installing, importing, or invoking a known public name
while the canonical package carries the real behavior. That promise needs to be
explicit so it does not quietly turn into a parallel product line.

## Continuity Rules

- preserve the legacy package name only as long as supported environments still
  need it
- keep the compatibility dependency aligned to the matching canonical version
- document the canonical replacement in package metadata, README text, and docs

## Review Questions

- does the compatibility package still preserve a real environment dependency
- is the canonical target still obvious from package metadata and docs
- is continuity being used as a bridge or as an excuse to avoid migration work

## Purpose

This page explains the dependency continuity model that keeps compatibility
packages narrow and honest.

## Stability

Keep it aligned with the actual package dependency and metadata strategy.
