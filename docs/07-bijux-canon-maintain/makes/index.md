---
title: makes
audience: mixed
type: index
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-26
---

# makes

Use this section to understand the shared Make surface that ties repository
operations together.

The make system is a real interface in this repository. It exposes local work,
CI checks, package dispatch, schema checks, and release-oriented automation
through stable command surfaces instead of one-off shell habits.

```mermaid
flowchart TB
    root["Makefile and makes/root.mk<br/>top-level entrypoints"]
    env["env.mk<br/>shared environment contract"]
    packages["packages.mk and makes/packages/*.mk<br/>package dispatch"]
    apis["api-freeze.mk and bijux-py/api*.mk<br/>schema and contract checks"]
    publish["publish.mk and bijux-docs.mk<br/>release and docs surfaces"]
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    classDef action fill:var(--bijux-mermaid-action-fill),stroke:var(--bijux-mermaid-action-stroke),color:var(--bijux-mermaid-action-text);
    class root page;
    class env,packages positive;
    class apis anchor;
    class publish action;
    root --> env
    root --> packages
    root --> apis
    root --> publish
```

## Pages In makes

- [Make System Overview](https://bijux.io/bijux-canon/07-bijux-canon-maintain/makes/make-system-overview/)
- [Root Entrypoints](https://bijux.io/bijux-canon/07-bijux-canon-maintain/makes/root-entrypoints/)
- [Environment Model](https://bijux.io/bijux-canon/07-bijux-canon-maintain/makes/environment-model/)
- [Repository Layout](https://bijux.io/bijux-canon/07-bijux-canon-maintain/makes/repository-layout/)
- [Package Dispatch](https://bijux.io/bijux-canon/07-bijux-canon-maintain/makes/package-dispatch/)
- [CI Targets](https://bijux.io/bijux-canon/07-bijux-canon-maintain/makes/ci-targets/)
- [Package Contracts](https://bijux.io/bijux-canon/07-bijux-canon-maintain/makes/package-contracts/)
- [Release Surfaces](https://bijux.io/bijux-canon/07-bijux-canon-maintain/makes/release-surfaces/)
- [Authoring Rules](https://bijux.io/bijux-canon/07-bijux-canon-maintain/makes/authoring-rules/)

## Use makes When

- the concern is about shared Make entrypoints rather than package code itself
- you need to understand how local commands, CI targets, and release commands
  are routed
- you are editing the repository command surface that other maintainers depend
  on

## Move On When

- the question is about GitHub Actions trigger logic instead of Make routing
- the issue belongs to a product package contract rather than a shared command
  layer
- you only need one concrete target and already know which page documents it

## Choose A Page

- use [Make System Overview](https://bijux.io/bijux-canon/07-bijux-canon-maintain/makes/make-system-overview/) for the broad structure
  first
- use [Root Entrypoints](https://bijux.io/bijux-canon/07-bijux-canon-maintain/makes/root-entrypoints/) when the concern starts at the
  top-level command surface
- use [Package Dispatch](https://bijux.io/bijux-canon/07-bijux-canon-maintain/makes/package-dispatch/) when the question is how shared
  targets route into one package or many
- use [CI Targets](https://bijux.io/bijux-canon/07-bijux-canon-maintain/makes/ci-targets/) or [Release Surfaces](https://bijux.io/bijux-canon/07-bijux-canon-maintain/makes/release-surfaces/)
  when the concern is automation-facing rather than developer-facing

## Concrete Anchors

- `Makefile` for the top-level command surface
- `makes/root.mk` and `makes/env.mk` for shared root composition
- `makes/packages.mk` and `makes/packages/*.mk` for per-package routing
- `makes/api-freeze.mk`, `makes/bijux-py/api.mk`, and related API includes for contract checks
- `makes/publish.mk` and `makes/bijux-docs.mk` for publication-oriented surfaces

## Command Surface Standard

The shared Make layer should make repository procedure easier to see, not
harder. If a critical command path only makes sense after reading several
include files in order, this section should expose that structure explicitly.
