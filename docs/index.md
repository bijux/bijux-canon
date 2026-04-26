---
title: bijux-canon Documentation
audience: mixed
type: index
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-26
---

# Bijux Canon

`bijux-canon` is a deliberately split system for deterministic ingest,
retrieval, reasoning, orchestration, and governed execution. The split
is the architecture, not a packaging afterthought. Each package owns one
kind of promise clearly enough that readers can understand the system by
skimming the docs instead of reconstructing intent from the tree.

Start here when you need repository-level orientation. A reader who opens only
this page should still be able to answer three things quickly: why the split
exists, which package owns the current concern, and where to go next without
guessing from the tree.

<!-- bijux-canon-badges:generated:start -->
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://pypi.org/project/bijux-canon-runtime/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-0F766E)](https://github.com/bijux/bijux-canon/blob/main/LICENSE)
[![Verify](https://github.com/bijux/bijux-canon/actions/workflows/verify.yml/badge.svg?branch=main)](https://github.com/bijux/bijux-canon/actions/workflows/verify.yml?query=branch%3Amain)
[![Release PyPI](https://github.com/bijux/bijux-canon/actions/workflows/release-pypi.yml/badge.svg)](https://github.com/bijux/bijux-canon/actions/workflows/release-pypi.yml)
[![Release GHCR](https://github.com/bijux/bijux-canon/actions/workflows/release-ghcr.yml/badge.svg)](https://github.com/bijux/bijux-canon/actions/workflows/release-ghcr.yml)
[![Release GitHub](https://github.com/bijux/bijux-canon/actions/workflows/release-github.yml/badge.svg)](https://github.com/bijux/bijux-canon/actions/workflows/release-github.yml)
[![Docs](https://github.com/bijux/bijux-canon/actions/workflows/deploy-docs.yml/badge.svg)](https://github.com/bijux/bijux-canon/actions/workflows/deploy-docs.yml)
[![Release](https://img.shields.io/github/v/release/bijux/bijux-canon?display_name=tag&label=release)](https://github.com/bijux/bijux-canon/releases)
[![GHCR packages](https://img.shields.io/badge/ghcr-10%20packages-181717?logo=github)](https://github.com/bijux?tab=packages&repo_name=bijux-canon)
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

[![bijux-canon-runtime](https://img.shields.io/badge/runtime-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-runtime)
[![bijux-canon-agent](https://img.shields.io/badge/agent-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-agent)
[![bijux-canon-ingest](https://img.shields.io/badge/ingest-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-ingest)
[![bijux-canon-reason](https://img.shields.io/badge/reason-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-reason)
[![bijux-canon-index](https://img.shields.io/badge/index-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-index)
[![agentic-flows](https://img.shields.io/badge/agentic--flows-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fagentic-flows)
[![bijux-agent](https://img.shields.io/badge/bijux--agent-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-agent)
[![bijux-rag](https://img.shields.io/badge/bijux--rag-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-rag)
[![bijux-rar](https://img.shields.io/badge/bijux--rar-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-rar)
[![bijux-vex](https://img.shields.io/badge/bijux--vex-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-vex)

[![bijux-canon-runtime docs](https://img.shields.io/badge/docs-runtime-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/bijux-canon-runtime/)
[![bijux-canon-agent docs](https://img.shields.io/badge/docs-agent-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/bijux-canon-agent/)
[![bijux-canon-ingest docs](https://img.shields.io/badge/docs-ingest-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/bijux-canon-ingest/)
[![bijux-canon-reason docs](https://img.shields.io/badge/docs-reason-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/bijux-canon-reason/)
[![bijux-canon-index docs](https://img.shields.io/badge/docs-index-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/bijux-canon-index/)
<!-- bijux-canon-badges:generated:end -->

<div class="bijux-callout"><strong>Start with the package split, not the file tree.</strong>
Ingest prepares deterministic material. Index executes retrieval and captures provenance. Reason turns evidence into inspectable claims. Agent coordinates role-based work. Runtime governs replay, persistence, and final acceptance. The repository handbook exists to explain how those responsibilities fit together without pretending they are one thing.</div>

If you only remember one idea, remember this: the split protects clarity.
Each package can stay strong because it is not also trying to absorb the
whole system.

<div class="bijux-panel-grid">
  <div class="bijux-panel"><h3>Whole-System Idea</h3><p>Use the root pages to understand why the repository is split and how the five canonical packages fit into one accountable flow.</p></div>
  <div class="bijux-panel"><h3>Honesty Rule</h3><p>Use the docs as a map, then verify the claim in code, schemas, tests, or release assets before treating it as settled.</p></div>
  <div class="bijux-panel"><h3>Fast Reading Path</h3><p>Open the repository handbook for cross-package questions, one product handbook for owned behavior, the maintainer handbook for repository health, and compatibility docs only for legacy names.</p></div>
</div>

<div class="bijux-quicklinks">
<a class="md-button md-button--primary" href="01-bijux-canon/">Open the repository handbook</a>
<a class="md-button" href="07-bijux-canon-maintain/">Open maintenance docs</a>
<a class="md-button" href="08-compat-packages/">Open compatibility docs</a>
</div>

## Visual Summary

```mermaid
flowchart TB
    reader["reader question<br/>which handbook owns my question?"]
    ingest["Ingest<br/>prepare deterministic material"]
    index["Index<br/>execute retrieval and capture provenance"]
    reason["Reason<br/>turn evidence into inspectable claims"]
    agent["Agent<br/>coordinate role-based work"]
    runtime["Runtime<br/>govern execution, replay, and persistence"]
    repo["Repository handbook<br/>shared rules and cross-package seams"]
    maintain["Maintenance handbook<br/>repository health and workflow authority"]
    compat["Compatibility handbook<br/>legacy names and migration pressure"]
    reader --> ingest
    reader --> index
    reader --> reason
    reader --> agent
    reader --> runtime
    reader --> repo
    reader --> maintain
    reader --> compat
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    classDef action fill:var(--bijux-mermaid-action-fill),stroke:var(--bijux-mermaid-action-stroke),color:var(--bijux-mermaid-action-text);
    class reader page;
    class ingest,index,reason,agent,runtime positive;
    class repo anchor;
    class maintain,compat action;
```

## Start Here

- open [Repository Handbook](01-bijux-canon/index.md) when the question crosses package boundaries or touches shared governance
- open one product package when you need ownership, interfaces, operations, or proof for one owned behavior surface
- open [Maintainer Handbook](07-bijux-canon-maintain/index.md) for repository automation, schema enforcement, and maintainer-only guardrails
- open [Compatibility Handbook](08-compat-packages/index.md) only when a legacy distribution, import, or command name is part of the problem

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
- `packages/` as the canonical package split this page is explaining

## Use This Page When

- you are orienting yourself before opening a repository, package, maintainer, or compatibility page
- you need the fastest route to the correct handbook section
- you are reviewing whether the current docs system covers the right surfaces

## Do Not Use This Page When

- the real question already belongs to one package and you need exact interfaces, workflows, or tests
- you need maintainer automation details rather than package or repository orientation
- you are reading a legacy name and already know you are in migration territory

## Read The Split This Way

Treat the split as a chain of accountable promises. Ingest makes source material deterministic enough to hand off. Index makes retrieval executable and provenance-rich. Reason makes evidence reviewable as claims. Agent coordinates multi-role work without hiding the trace. Runtime decides whether a run is acceptable, replayable, and durable. The repository handbook explains shared rules across those seams. The maintainer handbook explains how the repository stays healthy. The compatibility handbook exists to retire old names honestly rather than pretend they still define the system.

## Reader Takeaway

Use this page to choose the right handbook branch fast. If a reader still cannot tell whether the issue is repository-wide, package-local, maintainer-only, or legacy-only after this page, then the root story is still not clear enough.

## Purpose

Use this page to get oriented quickly, choose the right handbook branch,
and move to the files that carry the detailed proof.

## Stability

This page is part of the canonical docs spine. Keep it aligned with the sections rendered in `docs/`, the packages that still ship from this repository, and the reasons the split exists.
