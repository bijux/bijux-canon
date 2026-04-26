---
title: Make System Overview
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-09
---

# Make System Overview

The repository make system is the shared command language for maintenance work.

It starts at `Makefile`, which delegates immediately to `makes/root.mk`. From
there the repository pulls in a layered set of make fragments: environment
setup, repository-wide orchestration, package dispatch, shared `bijux-py`
contracts, CI-oriented targets, and per-package definitions.

## Core Shape

- `Makefile` is the top-level entrypoint
- `makes/root.mk` assembles repository-wide includes
- `makes/bijux-py/` carries reusable make contracts and target groups
- `makes/packages/` maps shared target patterns onto repository packages

## Bottom Line

This structure keeps the command layer explicit. A target can be traced to the
file that owns it, and a reviewer can tell whether a new target is repository
scope, package scope, CI scope, or release scope.

