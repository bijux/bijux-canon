---
title: Lifecycle Overview
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-26
---

# Lifecycle Overview

The runtime lifecycle starts when lower-package work reaches an authority entrypoint and ends when the run has been accepted, persisted, and made replayable under explicit policy.

## Lifecycle Shape

- runtime receives outputs from lower packages through governed entrypoints
- authority logic decides acceptance, persistence, verification, and replay behavior
- durable run records and traces leave the package as replayable runtime artifacts

## Handoff Point

The lifecycle stops at governed run artifacts. Repository maintenance is a separate concern owned by the maintenance handbook.

## Bottom Line

The lifecycle should stop exactly where package ownership stops. If the story needs another package to finish explaining itself, the boundary is already blurred.
