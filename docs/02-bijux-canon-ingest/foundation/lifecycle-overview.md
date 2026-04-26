---
title: Lifecycle Overview
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-04-26
---

# Lifecycle Overview

The ingest lifecycle starts with raw source material and ends when prepared output is stable enough for search to trust. It should not continue into retrieval interpretation or claim production.

## Lifecycle Shape

- input enters through package interfaces and configuration surfaces
- processing normalizes and chunks the material into predictable internal forms
- retrieval-side assembly shapes the output into handoff records and artifacts

## Handoff Point

The lifecycle stops at prepared output. `bijux-canon-index` owns what happens when that output becomes searchable behavior.

## Bottom Line

The lifecycle should stop exactly where package ownership stops. If the story needs another package to finish explaining itself, the boundary is already blurred.
