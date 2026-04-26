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

## Reader Route

- open this page when the main question is how compatibility packages keep
  installs, imports, or command names continuous during migration
- open `https://bijux.io/bijux-canon/08-compat-packages/migration/compatibility-overview/`
  for the broader compatibility model
- open `https://bijux.io/bijux-canon/08-compat-packages/migration/retirement-conditions/`
  when the question turns into when continuity is no longer needed

