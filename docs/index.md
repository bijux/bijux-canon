---
title: bijux-canon Documentation
audience: mixed
type: index
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-26
---

# Bijux Canon

`bijux-canon` is a package system for deterministic ingest, retrieval,
reasoning, orchestration, and governed execution. Use this site to find the
package that owns the behavior you are reviewing and the repository rules
that connect one package boundary to the next.

The split is the design. Each package owns one operational promise strongly
enough that you can follow the full system as a chain of accountable
handoffs instead of treating the repository as one blurred codebase.

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

<div class="bijux-callout"><strong>Start with owned promises, not with directory names.</strong>
Ingest prepares deterministic material. Index executes retrieval and preserves provenance. Reason turns evidence into inspectable claims. Agent coordinates role-based work with explicit traces. Runtime governs execution, replay, persistence, and final acceptability. The repository handbook explains the seams without pretending the root owns package behavior.</div>

<div class="bijux-panel-grid">
  <div class="bijux-panel"><h3>System Shape</h3><p>Five canonical packages carry the product flow, the root explains shared coordination, the maintainer handbook explains repository health, and compatibility docs exist only to bridge old names.</p></div>
  <div class="bijux-panel"><h3>Integrity Rule</h3><p>Statements here must stay consistent with checked-in code, schemas, tests, release assets, and published package boundaries.</p></div>
  <div class="bijux-panel"><h3>Fast Route</h3><p>Use the repository handbook for cross-package seams, a product handbook for owned behavior, the maintainer handbook for automation, and compatibility docs only when a legacy package name is still in play.</p></div>
</div>

<div class="bijux-quicklinks">
<a class="md-button md-button--primary" href="https://bijux.io/bijux-canon/01-bijux-canon/">Open the repository handbook</a>
<a class="md-button" href="https://bijux.io/bijux-canon/07-bijux-canon-maintain/">Open maintenance docs</a>
<a class="md-button" href="https://bijux.io/bijux-canon/08-compat-packages/">Open compatibility docs</a>
</div>

## Visual Summary

```mermaid
flowchart LR
    sources["source material<br/>documents and inputs"]
    ingest["bijux-canon-ingest<br/>deterministic preparation"]
    index["bijux-canon-index<br/>retrieval plus provenance"]
    reason["bijux-canon-reason<br/>claims plus verification"]
    agent["bijux-canon-agent<br/>role-based orchestration"]
    runtime["bijux-canon-runtime<br/>governed execution and replay"]
    repo["repository handbook<br/>shared boundaries and root rules"]
    maintain["maintenance handbook<br/>automation, make, workflows"]
    compat["compatibility packages<br/>legacy names under retirement pressure"]
    sources --> ingest --> index --> reason --> agent --> runtime
    repo --> ingest
    repo --> index
    repo --> reason
    repo --> agent
    repo --> runtime
    maintain --> repo
    compat --> ingest
    compat --> index
    compat --> reason
    compat --> agent
    compat --> runtime
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    classDef action fill:var(--bijux-mermaid-action-fill),stroke:var(--bijux-mermaid-action-stroke),color:var(--bijux-mermaid-action-text);
    class ingest,index,reason,agent,runtime positive;
    class sources,compat caution;
    class maintain action;
    class repo anchor;
```

## Start Here

- use the [Repository Handbook](https://bijux.io/bijux-canon/01-bijux-canon/) when you need package boundaries, shared rules, or repository-wide workflow
- use one product handbook when you already know the behavior belongs to ingest, index, reason, agent, or runtime
- use the [Maintainer Handbook](https://bijux.io/bijux-canon/07-bijux-canon-maintain/) for automation, Make routing, CI contracts, and repository health
- use the [Compatibility Handbook](https://bijux.io/bijux-canon/08-compat-packages/) only when an older distribution name, import, or command name is still part of the environment

## Choose A Package

| Package | Owns | Use It When |
| --- | --- | --- |
| `bijux-canon-ingest` | document preparation, chunking, and ingest-facing boundaries | you need to understand how raw inputs become deterministic material |
| `bijux-canon-index` | vector execution, backend integration, and provenance-rich retrieval results | you are reviewing search or retrieval behavior rather than document preparation |
| `bijux-canon-reason` | evidence-aware reasoning, claims, and verification | you need to inspect how evidence becomes explainable conclusions |
| `bijux-canon-agent` | role-based orchestration and trace-backed agent workflows | you are reviewing how multi-step agent work is coordinated and explained |
| `bijux-canon-runtime` | governed execution, replay, persistence, and final acceptability | you need the authority layer that decides whether a run is acceptable and durable |

## Repository-Level Guides

- [Repository Handbook](https://bijux.io/bijux-canon/01-bijux-canon/) explains the root-owned design boundary, shared workflow, and package seams
- [Maintainer Handbook](https://bijux.io/bijux-canon/07-bijux-canon-maintain/) documents helper code, Make surfaces, and workflow contracts that keep the repository healthy
- [Compatibility Handbook](https://bijux.io/bijux-canon/08-compat-packages/) documents preserved legacy names and the migration pressure away from them

## Verify The Route

- `mkdocs.yml` for the published navigation source
- `packages/` for the package split this page is introducing
- `docs/` for the handbook entry pages that route readers into the repository
- `packages/bijux-canon-dev/src/bijux_canon_dev/docs/repository_docs_catalog.py` for the catalog tooling behind the handbook structure

## Read Across The Flow

Start with ingest when your work begins at source material or deterministic
preparation. Move to index when retrieval behavior or provenance becomes the
focus. Move to reason when you need claims, verification, or evidence
interpretation. Move to agent when you need orchestration, traces, or
role-based coordination. Move to runtime when the question is whether a run
is acceptable, replayable, and durable. Stay at the repository level only
for shared seams, at the maintainer level only for repository health, and in
compatibility docs only until the canonical target is clear.

## Use This Page When

- you are still deciding which handbook owns the topic
- the concern may be cross-package, maintainer-only, or legacy-only
- you want the shortest route from the site homepage to the right handbook branch

## Move To A Deeper Handbook When

- one product handbook already owns the behavior you need
- the next step is a concrete interface, workflow, schema, or test surface
- the work is already known to be a legacy-name migration issue

## Core Claim

`bijux-canon` stays understandable because each package carries one main
promise and hands off explicitly to the next layer. Use this page to choose
the right handbook, then let the owning package carry the detailed contract.
