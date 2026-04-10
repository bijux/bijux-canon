---
title: bijux-canon Documentation
audience: mixed
type: index
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-10
---

# Bijux Canon

`bijux-canon` is a deliberately split system for deterministic ingest,
retrieval, reasoning, orchestration, and governed execution. The split
is the architecture, not a packaging afterthought. Each package owns one
kind of promise clearly enough that readers can understand the system by
skimming the docs instead of reconstructing intent from the tree.

Start here when you need repository-level orientation. A new reader
should be able to see why the repository is split, which package owns
the current concern, and which checked-in files back the explanation.

[![Release](https://img.shields.io/github/v/release/bijux/bijux-canon?display_name=tag&label=release)](https://github.com/bijux/bijux-canon/releases)
[![GHCR bundles](https://img.shields.io/badge/ghcr-10%20bundles-181717?logo=github)](https://github.com/orgs/bijux/packages?repo_name=bijux-canon)
[![Published packages](https://img.shields.io/badge/published%20packages-10-2563EB)](https://github.com/bijux/bijux-canon/tree/main/packages)

[![bijux-canon-runtime](https://img.shields.io/pypi/v/bijux-canon-runtime?label=runtime&logo=pypi)](https://pypi.org/project/bijux-canon-runtime/)
[![bijux-canon-agent](https://img.shields.io/pypi/v/bijux-canon-agent?label=agent&logo=pypi)](https://pypi.org/project/bijux-canon-agent/)
[![bijux-canon-ingest](https://img.shields.io/pypi/v/bijux-canon-ingest?label=ingest&logo=pypi)](https://pypi.org/project/bijux-canon-ingest/)
[![bijux-canon-reason](https://img.shields.io/pypi/v/bijux-canon-reason?label=reason&logo=pypi)](https://pypi.org/project/bijux-canon-reason/)
[![bijux-canon-index](https://img.shields.io/pypi/v/bijux-canon-index?label=index&logo=pypi)](https://pypi.org/project/bijux-canon-index/)

[![agentic-flows](https://img.shields.io/pypi/v/agentic-flows?label=agentic--flows&logo=pypi)](https://pypi.org/project/agentic-flows/)
[![bijux-agent](https://img.shields.io/pypi/v/bijux-agent?label=bijux--agent&logo=pypi)](https://pypi.org/project/bijux-agent/)
[![bijux-rag](https://img.shields.io/pypi/v/bijux-rag?label=bijux--rag&logo=pypi)](https://pypi.org/project/bijux-rag/)
[![bijux-rar](https://img.shields.io/pypi/v/bijux-rar?label=bijux--rar&logo=pypi)](https://pypi.org/project/bijux-rar/)
[![bijux-vex](https://img.shields.io/pypi/v/bijux-vex?label=bijux--vex&logo=pypi)](https://pypi.org/project/bijux-vex/)

[![Runtime docs](https://img.shields.io/badge/docs-runtime-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/bijux-canon-runtime/)
[![Agent docs](https://img.shields.io/badge/docs-agent-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/bijux-canon-agent/)
[![Ingest docs](https://img.shields.io/badge/docs-ingest-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/bijux-canon-ingest/)
[![Reason docs](https://img.shields.io/badge/docs-reason-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/bijux-canon-reason/)
[![Index docs](https://img.shields.io/badge/docs-index-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/bijux-canon-index/)

<div class="bijux-callout"><strong>Start with the package split, not the file tree.</strong> 
Ingest prepares deterministic material. Index executes retrieval and
captures provenance. Reason turns evidence into inspectable claims.
Agent coordinates role-based work. Runtime governs replay, persistence,
and final acceptance. The repository handbook exists to explain how those
responsibilities fit together without pretending they are one thing.</div>

If you only remember one idea, remember this: the split protects clarity.
Each package can stay strong because it is not also trying to absorb the
whole system.

<div class="bijux-panel-grid">
  <div class="bijux-panel"><h3>Whole-System Idea</h3><p>Use the root pages to understand why the repository is split and how the five canonical packages fit into one accountable flow.</p></div>
  <div class="bijux-panel"><h3>Honesty Rule</h3><p>Use the docs as a map, then verify the claim in code, schemas, tests, or release assets before treating it as settled.</p></div>
  <div class="bijux-panel"><h3>Fast Reading Path</h3><p>Open the repository handbook for cross-package questions, one product handbook for owned behavior, the maintainer handbook for repository health, and compatibility docs only for legacy names.</p></div>
</div>

<div class="bijux-quicklinks">
<a class="md-button md-button--primary" href="bijux-canon/">Open the repository handbook</a>
<a class="md-button" href="bijux-canon-maintain/">Open maintenance docs</a>
<a class="md-button" href="compat-packages/">Open compatibility docs</a>
</div>

## Visual Summary

```mermaid
flowchart TB
    page["Bijux Canon<br/>clarifies: bijux-canon section | bijux-canon-maintain section | compatibility packages section"]
    classDef page fill:#dbeafe,stroke:#1d4ed8,color:#1e3a8a,stroke-width:2px;
    classDef positive fill:#dcfce7,stroke:#16a34a,color:#14532d;
    classDef caution fill:#fee2e2,stroke:#dc2626,color:#7f1d1d;
    classDef anchor fill:#ede9fe,stroke:#7c3aed,color:#4c1d95;
    classDef action fill:#fef3c7,stroke:#d97706,color:#7c2d12;
    detail1["why the split exists"]
    detail1 --> page
    detail2["where each package takes authority"]
    detail2 -.gives the reader orientation.-> page
    detail3["why the split protects clarity"]
    detail3 --> page
    detail4["repository handbook"]
    detail4 -.gives the reader orientation.-> page
    detail5["one product handbook"]
    detail5 --> page
    detail6["the fastest credible next section"]
    detail6 -.gives the reader orientation.-> page
    detail7["maintainer work"]
    detail7 --> page
    detail8["legacy-name migration"]
    detail8 -.gives the reader orientation.-> page
    detail9["questions that do not belong on the landing page"]
    detail9 --> page
    next1["interfaces next"]
    page --> next1
    next2["maintainer docs"]
    page --> next2
    next3["repository handbook"]
    page --> next3
    class page page;
    class detail1,detail2,detail3,detail4,detail5,detail6,detail7,detail8,detail9 anchor;
    class next1,next2,next3 action;
```

## Start Here

- open [bijux-canon](bijux-canon/index.md) when the question crosses package boundaries or touches shared governance
- open one product package when you need ownership, interfaces, operations, or proof for one package
- open [bijux-canon-maintain](bijux-canon-maintain/index.md) for repository automation, schema enforcement, and maintainer-only guardrails
- open [compatibility packages](compat-packages/index.md) only when a legacy distribution, import, or command name is part of the problem

## Package Flow

| Package | Owns | Open It When |
| --- | --- | --- |
| `bijux-canon-ingest` | document preparation, chunking, and ingest-facing boundaries | you need to understand how raw inputs become deterministic material |
| `bijux-canon-index` | vector execution, backend integration, and provenance-rich retrieval results | you are reviewing search or retrieval behavior rather than document preparation |
| `bijux-canon-reason` | evidence-aware reasoning, claims, and verification | you need to inspect how evidence becomes explainable conclusions |
| `bijux-canon-agent` | role-based orchestration and trace-backed agent workflows | you are reviewing how multi-step agent work is coordinated and explained |
| `bijux-canon-runtime` | governed execution, replay, persistence, and final acceptability | you need the authority layer that decides whether a run is acceptable and durable |

## Documentation Scope

- the bijux-canon section
- the bijux-canon-maintain section
- the compatibility packages section

## Concrete Anchors

- `docs/index.md` as the root routing page
- `mkdocs.yml` as the published navigation source
- `packages/bijux-canon-dev/src/bijux_canon_dev/docs/repository_docs_catalog.py` as the developer-side catalog tool

## Use This Page When

- you are orienting yourself before opening a repository, package, maintainer, or compatibility page
- you need the fastest route to the correct handbook section
- you are reviewing whether the current docs system covers the right surfaces

## Decision Rule

Use this page to decide which handbook branch owns the current question. If a reader still cannot tell whether the issue is repository-wide, package-local, maintainer-only, or legacy-only after reading this page, then the root story is not clear enough yet.

## What This Page Answers

- which handbook to open first for a given repository question
- how the repository, package, maintainer, and compatibility docs relate
- what the current documentation system is expected to cover

## Reviewer Lens

- check that the first useful next step is obvious within a few seconds
- look for package, maintainer, or compatibility material that is leaking back into the landing page
- confirm that the route described here still matches the rendered navigation and the actual handbook content

## Honesty Boundary

This page can route readers quickly, but it does not replace the package, maintainer, or compatibility pages that carry the detailed proof for those surfaces.

## Next Checks

- open the repository handbook when the question spans packages or shared governance
- open a product package handbook when the question is about owned behavior, interfaces, operations, or proof
- open the maintainer or compatibility handbooks only when the question is explicitly about those concerns

## Purpose

Use this page to get oriented quickly, choose the right handbook branch,
and move to the files that carry the detailed proof.

## Stability

This page is part of the canonical docs spine. Keep it aligned with the sections rendered in `docs/`, the packages that still ship from this repository, and the reasons the split exists.
