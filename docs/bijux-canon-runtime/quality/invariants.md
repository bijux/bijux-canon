---
title: Invariants
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-04
---

# Invariants

Invariants are the promises that should survive ordinary implementation change.

This page names the truths the package is trying hardest not to lose. If an
invariant changes, that should feel more like a design event than a routine code
edit.

Read the quality pages for `bijux-canon-runtime` as the proof frame around the package. They should explain how trust is earned, how risk stays visible, and why a passing local check is not always enough.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-runtime"] --> section["Quality"]
    section --> page["Invariants"]
    dest1["see proof"]
    dest2["see limitations"]
    dest3["judge done-ness"]
    page --> dest1
    page --> dest2
    page --> dest3
```

```mermaid
flowchart TD
    page["Invariants"]
    focus1["Proof surfaces"]
    page --> focus1
    focus1_1["tests/unit for api, contracts, core, interfaces, model, and runtime"]
    focus1 --> focus1_1
    focus1_2["tests/e2e for governed flow behavior"]
    focus1 --> focus1_2
    focus2["Risk anchors"]
    page --> focus2
    focus2_1["README.md"]
    focus2 --> focus2_1
    focus2_2["execution store records"]
    focus2 --> focus2_2
    focus3["Review bar"]
    page --> focus3
    focus3_1["Invariants"]
    focus3 --> focus3_1
    focus3_2["package trust after change"]
    focus3 --> focus3_2
```

## Invariant Anchors

- package boundary stays explicit
- interface and artifact contracts remain reviewable
- tests continue to prove the long-lived promises

## Supporting Tests

- tests/unit for api, contracts, core, interfaces, model, and runtime
- tests/e2e for governed flow behavior
- tests/regression and tests/smoke for replay and storage protection
- tests/golden for durable example fixtures

## Concrete Anchors

- tests/unit for api, contracts, core, interfaces, model, and runtime
- tests/e2e for governed flow behavior
- README.md

## Use This Page When

- you are reviewing tests, invariants, limitations, or ongoing risks
- you need evidence that the documented contract is actually defended
- you are deciding whether a change is truly done rather than merely implemented

## Decision Rule

Use `Invariants` to decide whether `bijux-canon-runtime` has actually earned trust after a change. If one narrow green check hides a wider contract, risk, or validation gap, the work is not done yet.

## Next Checks

- move to foundation when the risk appears to be boundary confusion rather than missing tests
- move to architecture when the proof gap points to structural drift
- move to interfaces or operations when the proof question is really about a contract or workflow

## Update This Page When

- test layout, invariant protection, or risk posture changes materially
- definition-of-done or validation practice changes in a way reviewers must understand
- known limitations or evidence expectations move with the codebase

## What This Page Answers

- what currently proves the `bijux-canon-runtime` contract instead of merely describing it
- which risks, limits, and assumptions still need explicit skepticism
- what a reviewer should be able to say before accepting a change as done

## Reviewer Lens

- compare the documented proof story with the actual test layout and release posture
- look for limitations or risks that should have moved with recent behavior changes
- verify that the claimed done-ness standard still reflects real validation practice

## Honesty Boundary

This page explains how `bijux-canon-runtime` is supposed to earn trust, but it does not claim that prose alone is enough. If the listed tests, checks, and review practice stop backing the story, the story has to change.

## Purpose

This page records the kinds of promises that should not drift casually.

## Stability

Keep it aligned with invariant-focused tests and documented package guarantees.

## What Good Looks Like

- `Invariants` leaves a reviewer able to say why the package should be trusted after a change
- tests, limitations, and risk language reinforce one another instead of competing
- the completion bar is demanding enough to prevent shallow acceptance

## Failure Signals

- `Invariants` says the package is protected but cannot show which proof closes which risk
- reviewers disagree on whether the work is done because the standard is too implicit
- limitations remain unchanged even when package behavior has obviously shifted

## Tradeoffs To Hold

- prefer broader proof over narrower green checks when the package contract is larger than one code path
- prefer visible limitations over a cleaner story that hides risk
- prefer a slightly slower approval path over granting `bijux-canon-runtime` trust without enough evidence

## Cross Implications

- changes here influence how all other `bijux-canon-runtime` sections should be trusted after modification
- foundation, architecture, interface, and operations claims all become weaker if proof expectations drift
- review discipline here determines whether neighboring sections remain explanatory or merely aspirational

## Approval Questions

- does `Invariants` show enough proof to trust `bijux-canon-runtime` after change
- have limitations and known risks moved with the code rather than staying stale
- does the acceptance bar protect the package contract rather than only one local behavior

## Evidence Checklist

- read `packages/bijux-canon-runtime/tests` with the page's proof claims in hand
- verify package metadata and release notes in `packages/bijux-canon-runtime` do not contradict the review standard
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

The core quality claim of `bijux-canon-runtime` is that tests, invariants, visible risks, and completion criteria jointly show whether the package is trustworthy after change.

## Why It Matters

If the quality pages for `bijux-canon-runtime` are weak, it becomes difficult to tell whether a change is genuinely safe or merely passes a narrow local check.

## If It Drifts

- reviewers cannot tell whether the listed proof still covers the real risk surface
- limitations stop being visible until they show up as rework later
- definition-of-done language drifts away from actual validation practice

## Representative Scenario

A change appears correct locally, but the reviewer still needs to know whether `bijux-canon-runtime` has actually satisfied its proof obligations before the work is accepted.

## Source Of Truth Order

- `packages/bijux-canon-runtime/tests` for executable proof
- `packages/bijux-canon-runtime/pyproject.toml` and release notes for declared constraints and change posture
- this page for the review lens that explains how to interpret that proof honestly

## Common Misreadings

- that a passing local test automatically satisfies the package review standard
- that documented risks stay valid even when the code and interfaces have changed around them
- that done-ness is only about implementation and not about proof, clarity, and release impact
