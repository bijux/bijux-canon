---
title: Release and Versioning
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-26
---

# Release and Versioning

Release behavior in `bijux-canon` is partly shared and partly package-local.
The repository owns the conventions that make the package family legible; the
packages own their published behavior.

## Shared Release Rules

- root commit rules live in `pyproject.toml`
- package versions are written to package-local `_version.py` files by Hatch VCS
- release support helpers live in `bijux-canon-dev`
- split release workflows publish package artifacts and release metadata

## Compatibility Triggers

Treat a release change as shared governance when it changes:

- commit semantics that affect version discovery or release notes
- shared release workflows or publication routing
- metadata or tagging rules that apply across more than one package
- compatibility expectations around package naming or public release surfaces

## First Proof Checks

- `pyproject.toml` for commit and versioning conventions
- `.github/workflows/release-*.yml` for publication behavior
- the affected package handbook when the question narrows to one package release surface

## Bottom Line

Release and versioning belong at the root only while the rule is genuinely
shared. Once the question is one package artifact or one package release proof,
the package should take over.
