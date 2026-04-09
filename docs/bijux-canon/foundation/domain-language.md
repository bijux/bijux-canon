---
title: Domain Language
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-09
---

# Domain Language

Stable language is part of the repository design.

This repository does not just store code. It stores distinctions that need to
survive years of review and maintenance. When the language drifts, people stop
knowing whether they are talking about a package contract, a root rule, a
maintenance concern, or a migration bridge. That is how blurry architecture
returns even when the directory tree still looks neat.

## Terms That Should Stay Stable

- `canonical package` means one of the publishable `bijux-canon-*` packages
  that owns real product behavior
- `repository handbook` means the root-level explanation of cross-package
  structure, governance, and decisions
- `maintenance handbook` means the maintainer-facing documentation rooted at
  `docs/bijux-canon-maintain/`
- `compatibility package` means a legacy-name bridge under `packages/compat-*`
  rather than a preferred long-term entrypoint
- `root governance` means repository-wide rules such as docs structure, schema
  storage, validation posture, and release coordination
- `proof surface` means the files that let a reader verify a claim, such as
  tests, schemas, workflow definitions, or metadata

## Naming Guidance

- prefer names that explain durable intent rather than temporary delivery
  sequence
- keep commit messages, filenames, and headings aligned with the same concept
- avoid creating synonyms for the same repository boundary unless there is a
  real semantic difference

## Why It Matters

When names are stable, reviewers can move from a discussion to a file or a
test quickly. When names are unstable, every change starts with translation
work instead of understanding.

## Purpose

This page records the vocabulary that should remain consistent across docs,
code, metadata, and review conversations.

## Stability

Change this page only when the repository meaning of a term actually changes,
not when a new wording happens to sound fashionable.
