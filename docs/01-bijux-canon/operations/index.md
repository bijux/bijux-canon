---
title: Operations
audience: mixed
type: index
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-09
---

# Operations

The operations section explains how the repository is run, reviewed, and kept
coherent after the foundation has already made the ownership model clear.

These pages are about repeatable repository work rather than package-local
behavior. They should help a maintainer move from a question about setup,
validation, release flow, automation, or review posture to the concrete files
that carry that work today. The point is not to create ceremony. The point is
to keep operational memory checked in and inspectable.

## Pages in This Section

- [Local Development](local-development.md)
- [Testing and Validation](testing-and-validation.md)
- [Release and Versioning](release-and-versioning.md)
- [API and Schema Governance](api-and-schema-governance.md)
- [Contributor Workflows](contributor-workflows.md)
- [Automation Surfaces](automation-surfaces.md)
- [Artifact Governance](artifact-governance.md)
- [Review Expectations](review-expectations.md)
- [Change Management](change-management.md)

## What This Section Covers

- how repository-wide work should be carried out from checked-in assets
- where shared automation lives and what kinds of work it is allowed to do
- how release, review, validation, and artifact handling fit together at the
  repository boundary

## Read This Section When

- you are performing repository-wide work instead of one package-local change
- you need the operational truth for shared automation, release, or validation
- you are checking whether a proposed workflow is explicit enough to maintain

## Purpose

This page gives maintainers the shortest route into the repository’s operational
guidance without forcing them to infer it from CI logs or Make targets first.

## Stability

Keep this page aligned with the operational topics that actually matter at the
repository level.
