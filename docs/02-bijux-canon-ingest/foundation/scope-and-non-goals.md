---
title: Scope and Non-Goals
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-04-26
---

# Scope and Non-Goals

The scope of `bijux-canon-ingest` is narrower than “anything near the front of the pipeline.” It owns preparation work that makes later packages less ambiguous, not work that makes them less inconvenient.

## In Scope

- cleaning, normalization, and chunking before search begins
- ingest records and artifacts that become the explicit handoff into downstream packages
- package-local interfaces and safeguards required to run ingest work repeatably

## Non-Goals

- deciding retrieval quality, search replay, or vector-store behavior
- deciding what evidence means once claims and checks are being formed
- deciding whether a run is durable, governed, or acceptable to keep

## Scope Check

If the change makes later packages depend on ingest for anything beyond prepared input, the package is growing past its job.

## Bottom Line

A package boundary earns trust partly by the work it refuses to absorb. `bijux-canon-ingest` should stay narrow enough that its role can still be explained in one pass.
