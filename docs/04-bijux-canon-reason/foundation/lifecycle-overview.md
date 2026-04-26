---
title: Lifecycle Overview
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-04-26
---

# Lifecycle Overview

The reasoning lifecycle starts when retrieved evidence reaches a reasoning entrypoint and ends when claims and checks are explicit enough for a reviewer or downstream package to inspect.

## Lifecycle Shape

- evidence reaches the package through controlled interfaces and reasoning inputs
- package logic forms claims, runs checks, and records provenance under named ownership
- artifacts leave the package as inspectable reasoning outputs rather than raw retrieval output

## Handoff Point

The lifecycle stops before role coordination and run authority. Agent and runtime own those next layers.

## Bottom Line

The lifecycle should stop exactly where package ownership stops. If the story needs another package to finish explaining itself, the boundary is already blurred.
