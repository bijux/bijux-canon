---
title: Operator Workflows
audience: mixed
type: guide
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-04-04
---

# Operator Workflows

Operator workflows should start from documented package entrypoints and end in reviewable outputs.

## Workflow Anchors

- entry surfaces: CLI app in src/bijux_canon_reason/interfaces/cli, HTTP app in src/bijux_canon_reason/api/v1, schema files in apis/bijux-canon-reason/v1
- durable outputs: reasoning traces and replay diffs, claim and verification outcomes, evaluation suite artifacts
- validation backstops: tests/unit for planning, reasoning, execution, verification, and interfaces, tests/e2e for API, CLI, replay gates, retrieval reasoning, and smoke coverage

## Purpose

This page connects package interfaces to the workflows an operator actually performs.

## Stability

Keep it aligned with the existing commands, endpoints, and outputs.
