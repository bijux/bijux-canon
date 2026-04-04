---
title: Dependency Governance
audience: mixed
type: guide
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-04-04
---

# Dependency Governance

Dependency changes in `bijux-canon-reason` should be treated as contract changes when they
alter package authority, operational risk, or public setup expectations.

## Current Dependency Themes

- pydantic
- typer
- fastapi

## Purpose

This page explains why dependency review matters for the package.

## Stability

Keep it aligned with `pyproject.toml` and the package's real dependency posture.
