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

Read the quality pages for `bijux-canon-agent` as the proof frame around the package: they should explain how trust is earned, defended, and revised after change.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-agent"] --> section["Quality"]
    section --> page["Documentation Standards"]
    dest1["reviewable boundaries"]
    dest2["operator clarity"]
    dest3["change safety"]
    page --> dest1
    page --> dest2
    page --> dest3
```

```mermaid
flowchart TD
    page["Documentation Standards"]
    focus1["Owned package surface"]
    page --> focus1
    focus1_1["agent role implementations and role-specific helpers"]
    focus1 --> focus1_1
    focus1_2["deterministic orchestration of the local agent pipeline"]
    focus1 --> focus1_2
    focus2["Evidence to inspect"]
    page --> focus2
    focus2_1["src/bijux_canon_agent/agents"]
    focus2 --> focus2_1
    focus2_2["trace-backed final outputs"]
    focus2 --> focus2_2
    focus3["Review pressure"]
    page --> focus3
    focus3_1["Quality"]
    focus3 --> focus3_1
    focus3_2["tests/unit for local behavior and utility coverage"]
    focus3 --> focus3_2
```

## Standards

- use the shared five-category package spine
- prefer stable filenames that describe durable intent
- keep docs grounded in real code paths, interfaces, and artifacts

## Concrete Anchors

- tests/unit for local behavior and utility coverage
- tests/integration and tests/e2e for end-to-end workflow behavior
- README.md

## Use This Page When

- you are reviewing tests, invariants, limitations, or risk
- you need evidence that the documented contract is actually protected
- you are deciding whether a change is done rather than merely implemented

## Decision Rule

Use `Documentation Standards` to decide whether `bijux-canon-agent` has actually earned trust after a change. If the package passes one narrow check but leaves the wider contract, risk, or validation story unclear, the correct answer is that the work is not done yet.

## Next Checks

- move to foundation when the risk appears to be boundary confusion rather than missing tests
- move to architecture when the proof gap points to structural drift
- move to interfaces or operations when the proof question is really about a contract or workflow

## Update This Page When

- test layout, invariant protection, or risk posture changes materially
- definition-of-done or validation practice changes in a way reviewers must understand
- known limitations or evidence expectations move with the codebase

## What This Page Answers

- what proves the bijux-canon-agent contract today
- which risks or limits still need explicit review
- what a reviewer should verify before accepting change

## Reviewer Lens

- compare the documented proof strategy with the current test layout
- look for limitations or risks that should have been updated by recent changes
- verify that the page's definition of done still reflects real validation practice

## Honesty Boundary

This page explains how bijux-canon-agent protects itself, but it does not claim that prose alone is enough without the listed tests, checks, and review practice.

## Purpose

This page keeps package docs from drifting back into ad hoc structure.

## Stability

Update it only when the shared documentation system itself changes.

## What Good Looks Like

- `Documentation Standards` leaves a reviewer able to say why the package should be trusted after a change
- tests, limitations, and risk language reinforce one another instead of competing
- the completion bar is demanding enough to prevent shallow acceptance

## Failure Signals

- `Documentation Standards` says the package is protected but cannot show which proof closes which risk
- reviewers disagree on whether the work is done because the standard is too implicit
- limitations remain unchanged even when package behavior has obviously shifted

## Tradeoffs To Hold

- prefer broader proof over narrower green checks when the package contract is larger than one code path
- prefer visible limitations over a cleaner story that hides risk
- prefer a slightly slower approval path over granting `bijux-canon-agent` trust without enough evidence

## Cross Implications

- changes here influence how all other `bijux-canon-agent` sections should be trusted after modification
- foundation, architecture, interface, and operations claims all become weaker if proof expectations drift
- review discipline here determines whether neighboring sections remain explanatory or merely aspirational

## Approval Questions

- does `Documentation Standards` show enough proof to trust `bijux-canon-agent` after change
- have limitations and known risks moved with the code rather than staying stale
- does the acceptance bar protect the package contract instead of only one local behavior

## Evidence Checklist

- read `packages/bijux-canon-agent/tests` with the page's proof claims in hand
- verify package metadata and release notes in `packages/bijux-canon-agent` do not contradict the review standard
- check whether known limitations, risks, and completion language all moved together in the current change

## Anti-Patterns

- equating one local pass with full contract confidence
- keeping old risk prose after the code and tests have materially changed
- treating definition-of-done language as ceremonial rather than operational

## Escalate When

- the proof story can no longer be updated without revisiting adjacent sections
- a local validation gap reveals a larger boundary or architecture issue
- reviewers cannot agree on done-ness because the underlying contract changed

## Core Claim

The quality claim of `bijux-canon-agent` is that tests, invariants, risks, and completion criteria jointly prove whether the package is trustworthy after change.

## Why It Matters

If the quality pages for `bijux-canon-agent` are weak, it becomes difficult to tell whether a change is actually safe or merely passes a narrow local test.

## If It Drifts

- reviewers cannot tell whether the listed proof still covers the real risk surface
- limitations stop being visible until they show up as rework later
- definition-of-done language drifts away from actual validation practice

## Representative Scenario

A change appears correct locally, but the reviewer still needs to know whether `bijux-canon-agent` has actually satisfied its proof obligations before the work is accepted.

## Source Of Truth Order

- `packages/bijux-canon-agent/tests` for executable proof
- `packages/bijux-canon-agent/pyproject.toml` for declared package constraints
- this page for the review lens that explains how to read that proof

## Common Misreadings

- that a passing local test automatically satisfies the package review standard
- that documented risks are static and do not need to move with the code
- that the definition of done is only about implementation rather than proof
