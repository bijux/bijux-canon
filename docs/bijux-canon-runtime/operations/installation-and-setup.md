---
title: Installation and Setup
audience: mixed
type: guide
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-04
---

# Installation and Setup

Installation for `bijux-canon-runtime` should start from the package metadata and the specific
optional dependencies that matter for the work being done.

## Package Metadata Anchors

- package root: `packages/bijux-canon-runtime`
- metadata file: `packages/bijux-canon-runtime/pyproject.toml`
- readme: `packages/bijux-canon-runtime/README.md`

## Dependency Themes

- bijux-canon-agent
- bijux-canon-ingest
- bijux-canon-reason
- bijux-canon-index
- duckdb
- pydantic

## Purpose

This page tells maintainers where setup truth actually lives for the package.

## Stability

Keep it aligned with `pyproject.toml` and the checked-in package metadata.
