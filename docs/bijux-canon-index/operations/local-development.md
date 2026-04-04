---
title: Local Development
audience: mixed
type: guide
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-04
---

# Local Development

Local development should happen inside `packages/bijux-canon-index` with tests and docs updated
in the same change series as the code.

## Development Anchors

- tests/unit for API, application, contracts, domain, infra, and tooling
- tests/e2e for CLI workflows, API smoke, determinism gates, and provenance gates
- tests/conformance and tests/compat_v01 for compatibility behavior
- tests/stress and tests/scenarios for operational pressure checks

## Purpose

This page records the package-local development posture.

## Stability

Keep it aligned with the actual test layout and maintenance workflow.
