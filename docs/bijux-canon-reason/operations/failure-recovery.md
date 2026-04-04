---
title: Failure Recovery
audience: mixed
type: guide
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-04-04
---

# Failure Recovery

Failure recovery starts with knowing which artifacts, interfaces, and tests expose the problem.

## Recovery Anchors

- interface surfaces: CLI app in src/bijux_canon_reason/interfaces/cli, HTTP app in src/bijux_canon_reason/api/v1, schema files in apis/bijux-canon-reason/v1
- artifacts to inspect: reasoning traces and replay diffs, claim and verification outcomes, evaluation suite artifacts
- tests to run: tests/unit for planning, reasoning, execution, verification, and interfaces, tests/e2e for API, CLI, replay gates, retrieval reasoning, and smoke coverage

## Purpose

This page gives maintainers a durable frame for triaging package failures.

## Stability

Keep it aligned with the package entrypoints and diagnostic outputs.
