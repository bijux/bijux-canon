---
title: Lifecycle Overview
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-26
---

# Lifecycle Overview

The index lifecycle starts with prepared ingest output and ends when retrieval behavior has been executed, recorded, and exposed clearly enough for reasoning or runtime to inspect.

## Lifecycle Shape

- prepared input reaches index entrypoints and package workflows
- embedding, indexing, retrieval, and comparison logic execute under named module ownership
- results leave the package with provenance and replay context attached

## Handoff Point

The lifecycle stops before claim meaning or run authority. `bijux-canon-reason` and `bijux-canon-runtime` own those next decisions.

## Bottom Line

The lifecycle should stop exactly where package ownership stops. If the story needs another package to finish explaining itself, the boundary is already blurred.
