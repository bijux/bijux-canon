---
title: Authoring Rules
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-26
---

# Authoring Rules

The make layer stays maintainable only when new fragments follow the structure
that the existing tree is enforcing. A small naming or layout shortcut in the
command layer tends to become a repeated maintenance cost.

## Authoring Rules

- put shared logic in the narrowest reusable fragment that can honestly own it
- keep package bindings thin and descriptive
- prefer explicit variables and includes over hidden shell indirection
- place CI-only behavior in the CI fragment family rather than smearing it
  across unrelated targets
- document new durable command surfaces in this handbook when they become part
  of repository contract

## Failure Signs

- a target can be understood only by reading several unrelated fragments in
  order
- similar logic appears in multiple package binding files
- root entrypoints hide important behavior behind opaque shell commands

## First Proof Check

- new or changed fragment under `makes/`
- nearest reusable contract under `makes/bijux-py/`
- root or package caller that exposes the surface
