---
title: Quality Gates
audience: mixed
type: guide
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-04
---

# Quality Gates

Repository quality checks live here so package code does not each reinvent the
same maintenance logic.

## Current Quality Surfaces

- dependency analysis in `quality/deptry_scan.py`
- package-specific checks under `packages/`
- root test coverage through `packages/bijux-canon-dev/tests`

## Purpose

This page explains how the package participates in repository-wide correctness and consistency.

## Stability

Keep it aligned with the actual quality checks that run in tests or CI.
