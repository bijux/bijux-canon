---
title: Performance and Scaling
audience: mixed
type: guide
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-04
---

# Performance and Scaling

Performance work should preserve the deterministic and contract-driven behavior the package already promises.

## Performance Review Anchors

- inspect workflow modules before optimizing boundary code blindly
- use the package tests that exercise realistic workloads
- treat artifact and contract drift as a regression even when performance improves

## Test Anchors

- tests/unit for API, application, contracts, domain, infra, and tooling
- tests/e2e for CLI workflows, API smoke, determinism gates, and provenance gates
- tests/conformance and tests/compat_v01 for compatibility behavior
- tests/stress and tests/scenarios for operational pressure checks

## Purpose

This page records the posture for performance work in `bijux-canon-index`.

## Stability

Keep it aligned with the package's actual performance-sensitive paths and validation surfaces.
