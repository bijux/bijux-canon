---
title: Quality Gates
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-26
---

# Quality Gates

Repository quality gates live in `bijux-canon-dev` so packages do not reinvent
shared maintenance logic. The goal is not checklist volume. The goal is to keep
broad repository claims backed by named helpers, tests, and workflow entry
points.

## Current Gates

- dependency analysis in `quality/deptry_scan.py`
- docs publication and navigation contract tests in `tests/test_docs_*.py`
- repository contract coverage in tests such as
  `test_repository_api_contracts.py` and `test_repository_workflows.py`

## Why They Live Here

These checks defend repository shape rather than one package's product logic.
They belong in a shared maintainer package because their failure modes cross
package boundaries.

## First Proof Check

- `packages/bijux-canon-dev/src/bijux_canon_dev/quality`
- `packages/bijux-canon-dev/tests/test_docs_navigation_contract.py`
- `packages/bijux-canon-dev/tests/test_repository_workflows.py`
- workflow and `make` callers that run the checks

## Change Risk

A small maintainer gate can block every package in the matrix. Review changes by
asking whether the rule is still explicit, testable, and named at the same
level where it is enforced.
