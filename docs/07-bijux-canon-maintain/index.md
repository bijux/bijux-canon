---
title: Maintenance Handbook
audience: mixed
type: index
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-26
---

# Maintenance Handbook

The maintenance handbook explains the repository-owned operational surfaces that
do not belong in one product package handbook.

Schema drift checks, supply-chain helpers, shared Make targets, and CI workflow
contracts are real repository surfaces. They need first-class documentation so
repository health can be reviewed from checked-in rules instead of reverse
engineering shell glue and CI output.

## Visual Summary

```mermaid
flowchart TB
    maintenance["repository health<br/>shared operational authority"]
    dev["bijux-canon-dev<br/>helper code and policy enforcement"]
    makes["makes/<br/>command routing and package dispatch"]
    workflows["gh-workflows/<br/>verification, release, docs automation"]
    packages["canonical packages<br/>surfaces affected by shared maintenance"]
    maintenance --> dev
    maintenance --> makes
    maintenance --> workflows
    dev --> packages
    makes --> packages
    workflows --> packages
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    classDef action fill:var(--bijux-mermaid-action-fill),stroke:var(--bijux-mermaid-action-stroke),color:var(--bijux-mermaid-action-text);
    class maintenance page;
    class dev positive;
    class makes anchor;
    class workflows action;
    class packages caution;
```

## Sections

- [bijux-canon-dev](bijux-canon-dev/index.md) for maintainer package behavior,
  schema drift tooling, release support, SBOM helpers, and repository-health
  guardrails
- [makes](makes/index.md) for the shared make entrypoints, package dispatch,
  CI target families, and release-facing command surfaces
- [gh-workflows](gh-workflows/index.md) for GitHub Actions verification,
  publication, docs deployment, and reusable workflow contracts

## Use This Handbook When

- the question is about repository automation, verification, release support,
  workflow fan-out, or maintainer-only tooling
- you need to know which shared surface owns a repository-health rule
- the answer should stay above one product package boundary

## Do Not Start Here When

- the question is really about user-facing behavior in one canonical package
- the concern belongs to ingest, index, reasoning, agent, or runtime semantics
- you are tempted to treat maintainer tooling as the product surface itself

## Choose The Next Section By Question

- open [bijux-canon-dev](bijux-canon-dev/index.md) when the concern is helper
  code, schema drift, supply chain, release support, or quality gates
- open [makes](makes/index.md) when the concern is shared command surfaces,
  package dispatch, CI targets, or release entrypoints
- open [gh-workflows](gh-workflows/index.md) when the concern is GitHub Actions
  triggers, job trees, reusable workflows, or docs publication

## Shared Maintenance Anchors

- `packages/bijux-canon-dev` for maintainer helper code
- `makes/` for shared make entrypoints and composition
- `.github/workflows/` for CI, docs, and publication workflow truth

## Ownership Boundary

Maintenance documentation may explain repository-health behavior, but it does
not own product semantics. If a change primarily alters user-facing behavior,
the maintainer handbook should send the explanation back to the owning product
package instead of absorbing it.

## Maintainer Standard

Shared automation should remain understandable from checked-in helper code,
Make surfaces, and workflow contracts. Maintenance behavior that only exists as
habit or CI archaeology is still undocumented behavior.
