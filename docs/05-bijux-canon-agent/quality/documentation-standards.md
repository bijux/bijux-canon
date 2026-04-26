---
title: Documentation Standards
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-04-04
---

# Documentation Standards

Package docs should stay consistent with the shared handbook layout used across the repository.

Consistency matters here because readers should not need to relearn how to read
every package. The shared layout is part of the user experience, but honesty is
more important than uniformity for its own sake.

The quality pages show how trust is earned and where skepticism still belongs.

## Standards

- use the shared five-category package spine
- prefer stable filenames that describe durable intent
- keep docs grounded in real code paths, interfaces, and artifacts

## Concrete Anchors

- tests/unit for local behavior and utility coverage
- tests/integration and tests/e2e for end-to-end workflow behavior
- README.md

## Open This Page When

- you are reviewing tests, invariants, limitations, or ongoing risks
- you need evidence that the documented contract is actually defended
- you are deciding whether a change is truly done rather than merely implemented

## Decision Rule

Use `Documentation Standards` to decide whether `bijux-canon-agent` has actually earned trust after a change. If one narrow green check hides a wider contract, risk, or validation gap, the work is not done yet.

## What You Can Resolve Here

- what currently proves the `bijux-canon-agent` contract instead of merely describing it
- which risks, limits, and assumptions still need explicit skepticism
- what a reviewer should be able to say before accepting a change as done

## Review Focus

- compare the documented proof story with the actual test layout and release posture
- look for limitations or risks that should have moved with recent behavior changes
- verify that the claimed done-ness standard still reflects real validation practice

## Limits

Tests, checks, and review practice remain the proof for `bijux-canon-agent`. If they drift, this page is wrong.

## Read Next

- open foundation when the risk appears to be boundary confusion rather than missing tests
- open architecture when the proof gap points to structural drift
- open interfaces or operations when the proof question is really about a contract or workflow

