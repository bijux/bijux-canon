---
title: makes
audience: mixed
type: index
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-26
---

# makes

Open this section to understand the shared Make surface that ties repository
operations together.

The make system is a real interface in this repository. It exposes local work,
CI checks, package dispatch, schema checks, and release-oriented automation
through stable command surfaces instead of one-off shell habits.

## Pages In This Section

- [Make System Overview](https://bijux.io/bijux-canon/07-bijux-canon-maintain/makes/make-system-overview/)
- [Root Entrypoints](https://bijux.io/bijux-canon/07-bijux-canon-maintain/makes/root-entrypoints/)
- [Environment Model](https://bijux.io/bijux-canon/07-bijux-canon-maintain/makes/environment-model/)
- [Repository Layout](https://bijux.io/bijux-canon/07-bijux-canon-maintain/makes/repository-layout/)
- [Package Dispatch](https://bijux.io/bijux-canon/07-bijux-canon-maintain/makes/package-dispatch/)
- [CI Targets](https://bijux.io/bijux-canon/07-bijux-canon-maintain/makes/ci-targets/)
- [Package Contracts](https://bijux.io/bijux-canon/07-bijux-canon-maintain/makes/package-contracts/)
- [Release Surfaces](https://bijux.io/bijux-canon/07-bijux-canon-maintain/makes/release-surfaces/)
- [Authoring Rules](https://bijux.io/bijux-canon/07-bijux-canon-maintain/makes/authoring-rules/)

## Open This Section When

- the concern is about shared Make entrypoints rather than package code itself
- you need to understand how local commands, CI targets, and release commands
  are routed
- you are editing the repository command surface that other maintainers depend
  on

## Open Another Section When

- the question is about GitHub Actions trigger logic instead of Make routing
- the issue belongs to a product package contract rather than a shared command
  layer
- you only need one concrete target and already know which page documents it

## Start Here

- open [Make System Overview](https://bijux.io/bijux-canon/07-bijux-canon-maintain/makes/make-system-overview/) for the broad structure
  first
- open [Root Entrypoints](https://bijux.io/bijux-canon/07-bijux-canon-maintain/makes/root-entrypoints/) when the concern starts at the
  top-level command surface
- open [Package Dispatch](https://bijux.io/bijux-canon/07-bijux-canon-maintain/makes/package-dispatch/) when the question is how shared
  targets route into one package or many
- open [CI Targets](https://bijux.io/bijux-canon/07-bijux-canon-maintain/makes/ci-targets/) or [Release Surfaces](https://bijux.io/bijux-canon/07-bijux-canon-maintain/makes/release-surfaces/)
  when the concern is automation-facing rather than developer-facing

## Concrete Anchors

- `Makefile` for the top-level command surface
- `makes/root.mk` and `makes/env.mk` for shared root composition
- `makes/packages.mk` and `makes/packages/*.mk` for per-package routing
- `makes/api-freeze.mk`, `makes/bijux-py/api.mk`, and related API includes for contract checks
- `makes/publish.mk` and `makes/bijux-docs.mk` for publication-oriented surfaces

## Command Surface Standard

The shared Make layer exists to keep repository procedure visible instead of
hiding it. If a critical command path only makes sense after reading several
include files in order, this section should expose that structure explicitly.
