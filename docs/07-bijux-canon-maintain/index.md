---
title: Maintenance Handbook
audience: mixed
type: index
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-26
---

# Maintenance Handbook

Open this handbook to understand the repository-owned operational surfaces that
do not belong in one product package handbook.

Schema drift checks, supply-chain helpers, shared Make targets, and CI workflow
contracts are real repository surfaces. They need first-class documentation so
repository health can be reviewed from checked-in rules instead of reverse
engineering shell glue and CI output.

## Pages In This Handbook

- [bijux-canon-dev](https://bijux.io/bijux-canon/07-bijux-canon-maintain/bijux-canon-dev/) for maintainer package behavior,
  schema drift tooling, release support, SBOM helpers, and repository-health
  guardrails
- [makes](https://bijux.io/bijux-canon/07-bijux-canon-maintain/makes/) for the shared make entrypoints, package dispatch,
  CI target families, and release-facing command surfaces
- [gh-workflows](https://bijux.io/bijux-canon/07-bijux-canon-maintain/gh-workflows/) for GitHub Actions verification,
  publication, docs deployment, and reusable workflow contracts

## Open This Handbook When

- the question is about repository automation, verification, release support,
  workflow fan-out, or maintainer-only tooling
- you need to know which shared surface owns a repository-health rule
- the answer should stay above one product package boundary

## Open Another Handbook When

- the question is really about user-facing behavior in one canonical package
- the concern belongs to ingest, index, reasoning, agent, or runtime semantics
- you are tempted to treat maintainer tooling as the product surface itself

## Start Here

- open [bijux-canon-dev](https://bijux.io/bijux-canon/07-bijux-canon-maintain/bijux-canon-dev/) when the concern is helper
  code, schema drift, supply chain, release support, or quality gates
- open [makes](https://bijux.io/bijux-canon/07-bijux-canon-maintain/makes/) when the concern is shared command surfaces,
  package dispatch, CI targets, or release entrypoints
- open [gh-workflows](https://bijux.io/bijux-canon/07-bijux-canon-maintain/gh-workflows/) when the concern is GitHub Actions
  triggers, job trees, reusable workflows, or docs publication

## Concrete Anchors

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
