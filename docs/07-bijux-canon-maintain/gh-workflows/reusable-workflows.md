---
title: reusable-workflows
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-26
---

# reusable-workflows

Reusable workflows carry shared execution contracts that top-level entrypoints
call. In this repository they keep package verification and release artifact
creation consistent without pretending those files are standalone user entry
surfaces.

## Reuse Model

```mermaid
flowchart LR
    callers["top-level workflows"]
    reusable["reusable workflow contracts"]
    jobs["shared job shape"]
    proof["consistent verification and artifact behavior"]

    callers --> reusable --> jobs --> proof
```

This page should make reusable workflows read as shared contracts, not hidden
primary entrypoints. Their value is consistency across callers, not independent
workflow identity.

## Reusable Workflows

- `.github/workflows/ci.yml` for reusable package verification
- `.github/workflows/release-artifacts.yml` for reusable artifact build and
  staging

## Caller Boundary

These files matter because they define shared job shape, but the trigger and
intent still belong to their callers such as `verify.yml` and the release
workflows. Review them as shared contracts, not as independent product flows.

## First Proof Check

- `.github/workflows/ci.yml`
- `.github/workflows/release-artifacts.yml`
- callers in `verify.yml` and the release workflows

## Design Pressure

Reuse turns opaque when a maintainer can no longer tell whether a behavior is
owned by the caller or the reusable contract. The contract boundary has to stay
visible enough that review can follow responsibility.
