---
title: Performance and Scaling
audience: mixed
type: guide
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-04-04
---

# Performance and Scaling

Performance work should preserve the deterministic and contract-driven behavior the package already promises.

## Performance Review Anchors

- inspect workflow modules before optimizing boundary code blindly
- use the package tests that exercise realistic workloads
- treat artifact and contract drift as a regression even when performance improves

## Test Anchors

- tests/unit for planning, reasoning, execution, verification, and interfaces
- tests/e2e for API, CLI, replay gates, retrieval reasoning, and smoke coverage
- tests/perf for retrieval benchmark coverage
- tests/docs for documentation-linked safeguards

## Purpose

This page records the posture for performance work in `bijux-canon-reason`.

## Stability

Keep it aligned with the package's actual performance-sensitive paths and validation surfaces.
