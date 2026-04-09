---
title: Artifact Governance
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-09
---

# Artifact Governance

Generated output is part of repository clarity only when its status is obvious.

The repository needs a simple distinction between source, checked reference
artifacts, and disposable build output. Without that distinction, reviewers
waste time guessing whether a generated file is authoritative, incidental, or
stale.

## Artifact Classes

- tracked reference artifacts under `apis/` when schema review depends on them
- tracked release-facing or repository-facing evidence when the workflow needs a
  checked history of generated output
- generated local or CI output under `artifacts/` when it is part of validation
  rather than source

## Governance Rules

- keep tracked artifacts close to the rule they help prove
- avoid treating transient local output as if it were canonical source
- document which artifacts are reviewed and which are only produced during
  validation

## Concrete Anchors

- `apis/` for tracked schema evidence
- `artifacts/` for generated workflow output
- package `CHANGELOG.md` and build outputs for release-facing evidence

## Purpose

This page explains how the repository distinguishes durable reference artifacts
from generated workflow output.

## Stability

Update this page when the repository meaning of a tracked artifact class
changes.
