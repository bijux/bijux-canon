---
title: Foundation
audience: mixed
type: index
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-09
---

# Foundation

The foundation section explains why the repository exists in this shape before
it explains how the root is operated. A reader should leave this section able
to answer a small set of durable questions without guessing from directory
names: why the monorepo is split, where authority changes hands, which names
mean something stable, and what kind of change would damage that clarity.

This is the section to open when the repository still feels abstract. The goal
is to make the root legible as a design boundary, not as a pile of shared
files. If the foundation pages are healthy, later workflow and review pages can
assume the reader already understands what the repository is trying to protect.

## Pages in This Section

- [Platform Overview](platform-overview.md)
- [Repository Scope](repository-scope.md)
- [Workspace Layout](workspace-layout.md)
- [Package Map](package-map.md)
- [Ownership Model](ownership-model.md)
- [Domain Language](domain-language.md)
- [Documentation System](documentation-system.md)
- [Change Principles](change-principles.md)
- [Decision Rules](decision-rules.md)

## What This Section Covers

- the purpose of the repository split
- the shared vocabulary that should stay stable in code, docs, and review
- the ownership model that keeps root governance distinct from package behavior
- the design principles that make later operational choices easier to evaluate

## Read This Section When

- the monorepo shape is still more obvious than the monorepo intent
- you need to decide whether work belongs at the root or in a package
- you want the shortest route to the repository’s enduring design logic

## Purpose

This page gives readers a clean starting point for the repository foundation
without forcing them to skim all of the topic pages first.

## Stability

Keep this page aligned with the actual foundation topics that define the root
boundary and the names used across the repository.
