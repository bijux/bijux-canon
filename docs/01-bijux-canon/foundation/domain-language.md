---
title: Domain Language
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-26
---

# Domain Language

Stable language is part of the repository design.

`bijux-canon` does not just store code. It stores distinctions that need to
survive years of review: package contract versus root rule, maintainer
automation versus product behavior, and compatibility bridge versus canonical
surface.

## Terms That Should Stay Stable

- `canonical package` means one of the publishable `bijux-canon-*` packages
  that owns real product behavior
- `repository handbook` means the root-level explanation of cross-package
  structure, governance, and decisions
- `maintenance handbook` means the maintainer-facing documentation rooted at
  `docs/07-bijux-canon-maintain/`
- `compatibility package` means a legacy-name bridge under `packages/compat-*`
  rather than a preferred long-term entrypoint
- `proof surface` means the files that let a reader verify a claim, such as
  tests, schemas, workflow definitions, or metadata

## Terms To Avoid

- do not use `root package` when the subject is actually repository governance
- do not use `platform` as a synonym for any one product package
- do not use `public surface` for internal helper code that only supports one
  package implementation
- do not use `canonical` for compatibility material that exists only to bridge
  older names

## Review Consequence

Language drift is an architecture problem. If a reviewer cannot tell whether a
change belongs to a package, the root, maintenance tooling, or compatibility
material, the names are already failing.

## Bottom Line

Stable terms let a reader move from a discussion to a file, package, or test
quickly. Unstable terms force every review to start with translation instead of
understanding.
