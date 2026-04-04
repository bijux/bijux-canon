---
title: Security and Safety
audience: mixed
type: guide
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-04
---

# Security and Safety

Security review in `bijux-canon-index` should focus on the package's real boundary surfaces and outputs.

## Review Anchors

- CLI modules under src/bijux_canon_index/interfaces/cli
- HTTP app under src/bijux_canon_index/api
- OpenAPI schema files under apis/bijux-canon-index/v1

## Safety Rule

Any change that broadens package authority should update docs, tests, and release notes together.

## Purpose

This page keeps security review grounded in concrete package seams.

## Stability

Keep it aligned with the package interfaces and operational risk profile.
