---
title: Test Strategy
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-04
---

# Test Strategy

The tests for `bijux-canon-runtime` are the executable proof of its package contract.

This page should help readers see the broad proof shape of the package rather
than treating the test tree like a bag of unrelated checks. A good strategy page
explains why these tests exist, not just where they live.

Read the quality pages for `bijux-canon-runtime` as the proof frame around the package. They should explain how trust is earned, how risk stays visible, and why a passing local check is not always enough.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-runtime"] --> section["Quality"]
    section --> page["Test Strategy"]
    dest1["see proof"]
    dest2["see limitations"]
    dest3["judge done-ness"]
    page --> dest1
    page --> dest2
    page --> dest3
```

```mermaid
flowchart TD
    page["Test Strategy"]
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
    focus3_1["Test Strategy"]
    focus3 --> focus3_1
    focus3_2["package trust after change"]
    focus3 --> focus3_2
```

## Test Areas

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

Use `Test Strategy` to decide whether `bijux-canon-runtime` has actually earned trust after a change. If one narrow green check hides a wider contract, risk, or validation gap, the work is not done yet.

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

## Next Checks

- move to foundation when the risk appears to be boundary confusion rather than missing tests
- move to architecture when the proof gap points to structural drift
- move to interfaces or operations when the proof question is really about a contract or workflow

## Purpose

This page explains the broad testing shape of the package.

## Stability

Keep it aligned with the real test directories and the behaviors they protect.
