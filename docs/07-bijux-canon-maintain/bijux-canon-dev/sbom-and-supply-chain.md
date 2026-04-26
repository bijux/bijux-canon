---
title: SBOM and Supply Chain
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-26
---

# SBOM and Supply Chain

Supply-chain visibility is a repository-health concern, so SBOM helpers live in
`bijux-canon-dev` instead of being copied into every package. The point is not
just compliance language. The point is to keep dependency and provenance claims
backed by visible helpers and tests.

## Current Surfaces

- `sbom/requirements_writer.py` for requirements and SBOM-related output
- `tests/test_sbom_requirements_writer.py` for executable proof
- package `pyproject.toml` files and release artifacts that consume the output

## Why Repository Scope Matters

Supply-chain documentation becomes weak when every package improvises its own
rules. Shared helpers keep the generation path inspectable and reduce drift
between package metadata, build artifacts, and release attachments.

## First Proof Check

- `packages/bijux-canon-dev/src/bijux_canon_dev/sbom`
- `packages/bijux-canon-dev/tests/test_sbom_requirements_writer.py`
- callers in build and release workflows

## Boundary

This page documents shared provenance support. It does not claim that SBOM
output alone proves package behavior, security quality, or runtime trust.
