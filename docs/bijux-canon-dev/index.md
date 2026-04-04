---
title: bijux-canon-dev
audience: mixed
type: index
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-04
---

# bijux-canon-dev

`bijux-canon-dev` is the maintainer package for repository health. It exists so
quality gates, schema drift checks, SBOM generation, and release support have a
clear home that is outside the end-user product surface.

## Pages in This Section

- [Package Overview](package-overview.md)
- [Scope and Non-Goals](scope-and-non-goals.md)
- [Module Map](module-map.md)
- [Quality Gates](quality-gates.md)
- [Security Gates](security-gates.md)
- [Schema Governance](schema-governance.md)
- [Release Support](release-support.md)
- [SBOM and Supply Chain](sbom-and-supply-chain.md)
- [Operating Guidelines](operating-guidelines.md)

## Module Map

- `src/bijux_canon_dev/quality` for repository quality checks
- `src/bijux_canon_dev/security` for security gates
- `src/bijux_canon_dev/sbom` for supply-chain and bill-of-materials support
- `src/bijux_canon_dev/release` for release support
- `src/bijux_canon_dev/api` for OpenAPI and schema drift tooling
- `src/bijux_canon_dev/packages` for package-specific repository helpers

## Purpose

This page explains how to use the maintainer handbook without confusing it with user-facing product docs.

## Stability

Keep this page aligned with the actual maintainer modules that exist under `packages/bijux-canon-dev`.
