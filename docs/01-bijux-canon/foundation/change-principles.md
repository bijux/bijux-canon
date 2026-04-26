---
title: Change Principles
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-09
---

# Change Principles

Root-level change should leave the repository easier to explain, not merely
more featureful.

The repository exists to keep the package family legible. Changes that weaken
that legibility create long-term cost even when they solve a short-term
problem. The root therefore needs principles that make review stricter where
shared structure is at stake.

## Principles

- prefer moving behavior toward the owning package rather than broadening root
  scope by convenience
- keep documentation, schemas, tests, and workflow changes in the same review
  series when they describe the same behavior
- choose filenames, section names, and commit messages that will still make
  sense years later without relying on project memory
- keep root automation explicit about what it touches and why
- add compatibility shims only when they preserve a real migration path, not
  when they postpone a naming decision

## Review Pressure

Changes at the root deserve a little more skepticism because they can reshape
how the entire package family is read. A small root shortcut can create a large
maintenance shadow if it weakens the ownership model.

## What Good Looks Like

- the change clarifies one shared rule or structure instead of inventing a new
  ambiguous layer
- the proof surfaces move together with the explanation
- the resulting tree is more teachable to a new reader than it was before

