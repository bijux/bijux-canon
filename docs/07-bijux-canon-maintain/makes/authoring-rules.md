---
title: Authoring Rules
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-09
---

# Authoring Rules

The make layer stays maintainable only when new fragments follow the same
structure the existing tree is trying to preserve.

## Rules

- put shared logic in the narrowest reusable fragment that can honestly own it
- keep package bindings thin and descriptive
- prefer explicit variables and includes over hidden shell indirection
- place CI-only logic in the CI fragment family instead of smearing it across
  unrelated targets
- document new make surfaces in this handbook when they become part of the
  repository contract

## Review Questions

- is the new target in the right layer of the make tree
- does the file name explain its enduring job
- can a maintainer trace the target from the root entrypoint to the owning
  fragment without guesswork

