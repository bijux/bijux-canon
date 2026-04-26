---
title: Ownership Model
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-09
---

# Ownership Model

The repository is easiest to trust when ownership can be stated in layers
without hesitation.

The canonical packages own product behavior. They define the domain surfaces
that end users and downstream code are meant to depend on. The repository root
owns only what truly crosses package boundaries: shared documentation structure,
schema governance, build and validation coordination, and the release framing
that keeps the package family understandable as one system.

The maintenance handbook exists for repository health, not product behavior.
That distinction matters because maintainer tooling can affect many packages at
once. It should therefore explain and enforce repository rules without becoming
a second product layer above the packages. Compatibility material exists for a
different reason again: preserving legacy names while clearly pointing readers
toward the canonical package family.

## Ownership Layers

- product behavior belongs in `packages/bijux-canon-*`
- shared governance belongs in the repository handbook and root automation
- maintainer automation belongs in `packages/bijux-canon-dev` and the
  maintenance handbook
- legacy continuity belongs in `packages/compat-*` and the compatibility
  handbook

## Boundary Rule

If a change can be explained honestly from one package handbook, it usually
does not belong at the root. The root should absorb only cross-package truth,
never convenience.

## Review Questions

- does this work change a package contract or a repository rule
- would a package reader still understand the behavior without opening a root
  document
- is maintainer tooling clarifying package truth or quietly overriding it

