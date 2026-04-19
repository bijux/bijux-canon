---
title: Risk Register
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-04
---

# Risk Register

The durable risks for `bijux-canon-index` are the ones that make the package boundary, interface contract,
or produced artifacts harder to trust.

This page should keep long-lived risk language attached to the package instead
of scattering it across reviews and memory. The goal is not alarmism; it is to
help maintainers remember which failures would actually cost credibility.

Treat the quality pages for `bijux-canon-index` as the proof frame around the package. They should show how trust is earned and where skepticism still belongs.

## Visual Summary

```mermaid
flowchart LR
    page["Risk Register<br/>clarifies: see proof | see limitations | judge done-ness"]
    classDef page fill:#dbeafe,stroke:#1d4ed8,color:#1e3a8a,stroke-width:2px;
    classDef positive fill:#dcfce7,stroke:#16a34a,color:#14532d;
    classDef caution fill:#fee2e2,stroke:#dc2626,color:#7f1d1d;
    classDef anchor fill:#ede9fe,stroke:#7c3aed,color:#4c1d95;
    classDef action fill:#fef3c7,stroke:#d97706,color:#7c2d12;
    proof1["tests/e2e for CLI workflows, API smoke, determinism gates, and provenance gates"]
    proof1 --> page
    proof2["tests/conformance and tests/compat_v01 for compatibility behavior"]
    proof2 --> page
    proof3["tests/unit for API, application, contracts, domain, infra, and tooling"]
    proof3 --> page
    risk1["README.md"]
    risk1 -.keeps trust honest.-> page
    risk2["CHANGELOG.md"]
    risk2 -.keeps trust honest.-> page
    risk3["pyproject.toml"]
    risk3 -.keeps trust honest.-> page
    bar1["package trust after change"]
    page --> bar1
    bar2["proof before confidence"]
    page --> bar2
    bar3["done means defended behavior"]
    page --> bar3
    class page page;
    class proof1,proof2,proof3 positive;
    class risk1,risk2,risk3 caution;
    class bar1,bar2,bar3 action;
```

## Ongoing Risks to Watch

- hidden overlap with neighboring packages
- drift between docs, code, and tests
- compatibility changes that are not made explicit

## Concrete Anchors

- tests/unit for API, application, contracts, domain, infra, and tooling
- tests/e2e for CLI workflows, API smoke, determinism gates, and provenance gates
- README.md

## Use This Page When

- you are reviewing tests, invariants, limitations, or ongoing risks
- you need evidence that the documented contract is actually defended
- you are deciding whether a change is truly done rather than merely implemented

## Decision Rule

Use `Risk Register` to decide whether `bijux-canon-index` has actually earned trust after a change. If one narrow green check hides a wider contract, risk, or validation gap, the work is not done yet.

## What This Page Answers

- what currently proves the `bijux-canon-index` contract instead of merely describing it
- which risks, limits, and assumptions still need explicit skepticism
- what a reviewer should be able to say before accepting a change as done

## Reviewer Lens

- compare the documented proof story with the actual test layout and release posture
- look for limitations or risks that should have moved with recent behavior changes
- verify that the claimed done-ness standard still reflects real validation practice

## Honesty Boundary

This page explains how `bijux-canon-index` is supposed to earn trust, but it does not claim that prose alone is enough. If the listed tests, checks, and review practice stop backing the story, the story has to change.

## Next Checks

- move to foundation when the risk appears to be boundary confusion rather than missing tests
- move to architecture when the proof gap points to structural drift
- move to interfaces or operations when the proof question is really about a contract or workflow

## Purpose

This page keeps long-lived package risks visible to maintainers.

## Stability

Update it when the durable risk profile changes, not for routine day-to-day churn.
