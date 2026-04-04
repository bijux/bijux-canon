---
title: Execution Model
audience: mixed
type: guide
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-04-04
---

# Execution Model

`bijux-canon-ingest` executes work by receiving inputs at its interfaces, coordinating policy
and workflows in application code, and delegating specific responsibilities to owned modules.

## Execution Anchors

- entry surfaces: CLI entrypoint in src/bijux_canon_ingest/interfaces/cli/entrypoint.py, HTTP boundaries under src/bijux_canon_ingest/interfaces, configuration modules under src/bijux_canon_ingest/config
- workflow modules: src/bijux_canon_ingest/processing, src/bijux_canon_ingest/retrieval, src/bijux_canon_ingest/application
- outputs: normalized document trees, chunk collections and retrieval-ready records, diagnostic output produced during ingest workflows

## Purpose

This page summarizes the package execution model before readers inspect individual modules.

## Stability

Keep it aligned with the actual workflow code and entrypoints.
