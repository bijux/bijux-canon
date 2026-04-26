---
title: Dependency Governance
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-04-04
---

# Dependency Governance

Dependency changes in `bijux-canon-agent` should be treated as contract changes when they
alter package authority, operational risk, or public setup expectations.

This page keeps dependency review from feeling bureaucratic. Dependencies
matter because they reshape what the package relies on, what it exposes, and
what downstream maintainers must now trust.

Treat the quality pages for `bijux-canon-agent` as the proof frame around the package. They should show how trust is earned and where skepticism still belongs.

## Current Dependency Themes

- aiohttp
- typer
- click
- pydantic
- fastapi
- openai
- structlog
- pluggy

## Concrete Anchors

- tests/unit for local behavior and utility coverage
- tests/integration and tests/e2e for end-to-end workflow behavior
- README.md

## Open This Page When

- you are reviewing tests, invariants, limitations, or ongoing risks
- you need evidence that the documented contract is actually defended
- you are deciding whether a change is truly done rather than merely implemented

## Decision Rule

Use `Dependency Governance` to decide whether `bijux-canon-agent` has actually earned trust after a change. If one narrow green check hides a wider contract, risk, or validation gap, the work is not done yet.

## What You Can Resolve Here

- what currently proves the `bijux-canon-agent` contract instead of merely describing it
- which risks, limits, and assumptions still need explicit skepticism
- what a reviewer should be able to say before accepting a change as done

## Review Focus

- compare the documented proof story with the actual test layout and release posture
- look for limitations or risks that should have moved with recent behavior changes
- verify that the claimed done-ness standard still reflects real validation practice

## Limits

Tests, checks, and review practice remain the proof for this package. If they drift, this page is wrong.

## Read Next

- open foundation when the risk appears to be boundary confusion rather than missing tests
- open architecture when the proof gap points to structural drift
- open interfaces or operations when the proof question is really about a contract or workflow

