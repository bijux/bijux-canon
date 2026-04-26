---
title: Release and Versioning
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-04
---

# Release and Versioning

The repository uses commitizen for conventional commit messages and package
tags for version discovery through Hatch VCS. Version resolution is therefore
both a repository concern and a package concern.

The wording of the commit history matters here because the repository is meant
to stay understandable years later. A good commit message should explain
durable intent, not just what happened to be touched in one diff.

## Visual Summary

```mermaid
flowchart LR
    change["Release-ready change"]
    notes["Update changelog and version metadata"]
    workflows["Release workflows publish the result"]
    packages["Package artifacts stay aligned"]
    change --> notes --> workflows --> packages
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    classDef action fill:var(--bijux-mermaid-action-fill),stroke:var(--bijux-mermaid-action-stroke),color:var(--bijux-mermaid-action-text);
    class change page;
    class notes anchor;
    class workflows action;
    class packages positive;
```

## Shared Release Facts

- root commit rules live in `pyproject.toml`
- package versions are written to package-local `_version.py` files by Hatch VCS
- release support helpers live in `bijux-canon-dev`
- the split release workflows (`release-pypi.yml`, `release-ghcr.yml`, `release-github.yml`) publish package artifacts and release metadata

## Versioning Rule

Commit messages should communicate long-lived intent clearly enough that a
maintainer can understand them years later without opening the diff first.

## Concrete Anchors

- `pyproject.toml` for workspace metadata and commit conventions
- `Makefile` and `makes/` for root automation
- `apis/` and `.github/workflows/` for schema and validation review

## Open This Page When

- you are dealing with repository-wide seams rather than one package alone
- you need shared workflow, schema, or governance context before changing code
- you want the monorepo view that sits above the package handbooks

## Decision Rule

Use this page when release behavior depends on root conventions, shared
workflows, or version metadata that spans packages. If the answer depends
mostly on one package's local release behavior, open that package handbook
instead.

## What This Page Answers

- which shared release rule is in scope
- which workflows and metadata deserve inspection
- how repository release governance stops before package-local ownership

## Reviewer Lens

- compare the page claims with the real root files, workflows, or schema assets
- check that repository guidance still stops where package ownership begins
- confirm that any repository rule described here is still enforceable in code or automation

## Honesty Boundary

Repository guidance here does not replace the actual release workflows, package
metadata, or package-local release proof.

## Next Checks

- open the owning package docs when the question stops being repository-wide
- check root files, schemas, or workflows named here before trusting prose alone
- use the maintainer handbook at `https://bijux.io/bijux-canon/07-bijux-canon-maintain/`
  when the issue is really about release automation or drift tooling

## Purpose

This page connects root commit conventions to the package release mechanism.

## Stability

Keep this page aligned with the release tooling that is actually configured in the repository.
