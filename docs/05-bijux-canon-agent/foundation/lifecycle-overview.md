---
title: Lifecycle Overview
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-04-26
---

# Lifecycle Overview

The agent lifecycle starts when a workflow enters orchestration and ends when the coordinated result and its trace are clear enough for runtime or a caller to inspect.

## Lifecycle Shape

- workflow input enters through package interfaces and orchestration entrypoints
- roles and steps coordinate under deterministic workflow rules
- trace-backed artifacts and outputs leave the package for callers or runtime governance

## Handoff Point

The lifecycle stops before final acceptance and persistence. Runtime owns that last authority step.

## Bottom Line

The lifecycle should stop exactly where package ownership stops. If the story needs another package to finish explaining itself, the boundary is already blurred.
