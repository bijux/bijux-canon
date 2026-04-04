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
</div>

## Documentation Scope

- the bijux-canon section

## Reading Map

- start with [bijux-canon](bijux-canon/index.md) for repository-wide behavior
- move into one product package when you need ownership details or operator guidance
- maintainer automation pages are added when the dev section is rendered
- compatibility guidance is added when the compat section is rendered

## Purpose

This page routes readers into the canonical repository and package handbooks without mixing product ownership with maintenance-only or legacy-only concerns.

## Stability

This page is part of the canonical docs spine. Keep it aligned with the sections actually rendered in `docs/` and the packages that still ship from this repository.
