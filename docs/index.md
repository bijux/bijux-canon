---
title: bijux-canon Documentation
audience: mixed
type: index
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-04
---

# Docs Index

`bijux-canon` is the canonical documentation site for the monorepo, the five
product packages, the repository maintenance package, and the legacy
compatibility shims that still preserve older installation names.

<div class="bijux-callout"><strong>Use this site as the current contract.</strong> 
The sections beneath it are intentionally organized with one repository
handbook, one maintainer handbook, one compatibility handbook, and five
package handbooks that all share the same five-category spine.</div>

<div class="bijux-panel-grid">
  <div class="bijux-panel"><h3>Repository</h3><p>Explains the monorepo boundary, shared workflows, schemas, validation, and release intent.</p></div>
  <div class="bijux-panel"><h3>Packages</h3><p>Each canonical package uses the same foundation, architecture, interfaces, operations, and quality layout.</p></div>
  <div class="bijux-panel"><h3>Maintenance</h3><p>Separate sections cover the repository tooling package and the compatibility shims so their intent stays explicit.</p></div>
</div>

<div class="bijux-quicklinks">
<a class="md-button md-button--primary" href="bijux-canon/">Open the repository handbook</a>
<a class="md-button" href="bijux-canon-ingest/foundation/">bijux-canon-ingest</a>
<a class="md-button" href="bijux-canon-index/foundation/">bijux-canon-index</a>
<a class="md-button" href="bijux-canon-reason/foundation/">bijux-canon-reason</a>
<a class="md-button" href="bijux-canon-agent/foundation/">bijux-canon-agent</a>
<a class="md-button" href="bijux-canon-runtime/foundation/">bijux-canon-runtime</a>
<a class="md-button" href="bijux-canon-dev/">Open maintainer docs</a>
<a class="md-button" href="compat-packages/">Open compatibility docs</a>
</div>

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon"] --> section["Root Site"]
    section --> page["Docs Index"]
    dest1["bijux-canon section"]
    dest2["bijux-canon-ingest section"]
    dest3["bijux-canon-index section"]
    dest4["bijux-canon-reason section"]
    dest5["bijux-canon-agent section"]
    dest6["bijux-canon-runtime section"]
    dest7["bijux-canon-dev section"]
    dest8["compatibility packages section"]
    page --> dest1
    page --> dest2
    page --> dest3
    page --> dest4
    page --> dest5
    page --> dest6
    page --> dest7
    page --> dest8
```

## Documentation Scope

- the bijux-canon section
- the bijux-canon-ingest section
- the bijux-canon-index section
- the bijux-canon-reason section
- the bijux-canon-agent section
- the bijux-canon-runtime section
- the bijux-canon-dev section
- the compatibility packages section

## Reading Map

- start with [bijux-canon](bijux-canon/index.md) for repository-wide behavior
- move into one product package when you need ownership details or operator guidance
- use [bijux-canon-dev](bijux-canon-dev/index.md) for maintainer automation and quality gates
- use [compatibility packages](compat-packages/index.md) when tracing a legacy install name

## Purpose

This page routes readers into the canonical repository and package handbooks without mixing product ownership with maintenance-only or legacy-only concerns.

## Stability

This page is part of the canonical docs spine. Keep it aligned with the sections actually rendered in `docs/` and the packages that still ship from this repository.
