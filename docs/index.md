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
reasoning, orchestration, and governed execution. Open this site to find the
package that owns the behavior under review and the repository rules that keep
the package handoffs explicit.

The split is the design. Each package owns one operational promise strongly
enough that you can follow the full system as a chain of accountable
handoffs instead of treating the repository as one blurred codebase.

One concrete reading path makes that split easier to trust. A source document
is prepared by `bijux-canon-ingest`, turned into replayable retrieval behavior
by `bijux-canon-index`, translated into inspectable claims by
`bijux-canon-reason`, coordinated by `bijux-canon-agent`, and accepted or
replayed under `bijux-canon-runtime`. The root owns the rules that keep those
handoffs visible. It does not own the package behavior itself.

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
  <div class="bijux-panel"><h3>Fast Route</h3><p>Open the repository handbook for cross-package seams, a product handbook for owned behavior, the maintainer handbook for automation, and compatibility docs only when a legacy package name is still in play.</p></div>
</div>

<div class="bijux-quicklinks">
<a class="md-button md-button--primary" href="https://bijux.io/bijux-canon/01-bijux-canon/">Open the repository handbook</a>
<a class="md-button" href="https://bijux.io/bijux-canon/07-bijux-canon-maintain/">Open maintenance docs</a>
<a class="md-button" href="https://bijux.io/bijux-canon/08-compat-packages/">Open compatibility docs</a>
</div>

## System Map

```mermaid
flowchart LR
    source["source material<br/>documents, records, corpora"]
    ingest["bijux-canon-ingest<br/>prepare deterministic material"]
    index["bijux-canon-index<br/>execute retrieval with provenance"]
    reason["bijux-canon-reason<br/>turn evidence into claims"]
    agent["bijux-canon-agent<br/>coordinate role-based work"]
    runtime["bijux-canon-runtime<br/>govern execution and replay"]
    accepted["accepted run<br/>durable, inspectable, replayable"]
    repo["repository handbook<br/>boundaries, schemas, release rules"]
    maintain["maintenance handbook<br/>make, helper code, workflows"]
    compat["compatibility handbook<br/>legacy names under migration pressure"]

    source --> ingest --> index --> reason --> agent --> runtime --> accepted
    repo -. keeps boundaries visible .-> ingest
    repo -. keeps boundaries visible .-> index
    repo -. keeps boundaries visible .-> reason
    repo -. keeps boundaries visible .-> agent
    repo -. keeps boundaries visible .-> runtime
    maintain --> repo
    compat -. points old names to canonical owners .-> ingest
    compat -. points old names to canonical owners .-> index
    compat -. points old names to canonical owners .-> reason
    compat -. points old names to canonical owners .-> agent
    compat -. points old names to canonical owners .-> runtime

    classDef page fill:#eef6ff,stroke:#2563eb,color:#153145,stroke-width:2px;
    classDef positive fill:#eefbf3,stroke:#16a34a,color:#173622;
    classDef caution fill:#fff1f2,stroke:#dc2626,color:#6b1d1d;
    classDef anchor fill:#f4f0ff,stroke:#7c3aed,color:#47207f;
    classDef action fill:#fff4da,stroke:#d97706,color:#6b3410;
    class source,accepted page;
    class ingest,index,reason,agent,runtime positive;
    class repo anchor;
    class maintain,compat action;
```

## Start Here

- open the [Repository Handbook](https://bijux.io/bijux-canon/01-bijux-canon/) for package boundaries, shared rules, and repository-wide workflow
- open one product handbook when the behavior already belongs to ingest, index, reason, agent, or runtime
- open the [Maintenance Handbook](https://bijux.io/bijux-canon/07-bijux-canon-maintain/) for automation, Make routing, CI contracts, and repository health
- open the [Compatibility Handbook](https://bijux.io/bijux-canon/08-compat-packages/) only when an older distribution name, import, or command name is still active

## One Real Run

A useful mental model is a reviewable run. Each layer changes the question that
the next layer is allowed to ask. Ingest asks whether source material is stable
enough to hand forward. Index asks whether retrieval happened through an
auditable contract. Reason asks what the retrieved evidence supports. Agent
asks how the work should be coordinated. Runtime asks whether the full run can
be accepted, persisted, and replayed.

```mermaid
sequenceDiagram
    autonumber
    participant Reader
    participant Ingest
    participant Index
    participant Reason
    participant Agent
    participant Runtime

    Reader->>Ingest: provide source material
    Ingest-->>Index: deterministic chunks and preparation records
    Index-->>Reason: retrieved evidence with provenance and replay data
    Reason-->>Agent: claims, checks, and reasoning artifacts
    Agent-->>Runtime: ordered workflow trace and final package outputs
    Runtime-->>Reader: accepted, rejected, or replayable run verdict
```

## Package Handbooks

| Package | Owns | Open It When |
| --- | --- | --- |
| `bijux-canon-ingest` | document preparation, chunking, and ingest-facing boundaries | you need to understand how raw inputs become deterministic material |
| `bijux-canon-index` | vector execution, backend integration, and provenance-rich retrieval results | you are reviewing search or retrieval behavior rather than document preparation |
| `bijux-canon-reason` | evidence-aware reasoning, claims, and verification | you need to inspect how evidence becomes explainable conclusions |
| `bijux-canon-agent` | role-based orchestration and trace-backed agent workflows | you are reviewing how multi-step agent work is coordinated and explained |
| `bijux-canon-runtime` | governed execution, replay, persistence, and final acceptability | you need the authority layer that decides whether a run is acceptable and durable |

## Shared Handbooks

- [Repository Handbook](https://bijux.io/bijux-canon/01-bijux-canon/) explains the root-owned design boundary, shared workflow, and package seams
- [Maintainer Handbook](https://bijux.io/bijux-canon/07-bijux-canon-maintain/) documents helper code, Make surfaces, and workflow contracts that keep the repository healthy
- [Compatibility Handbook](https://bijux.io/bijux-canon/08-compat-packages/) documents preserved legacy names and the migration pressure away from them

## Concrete Anchors

- `mkdocs.yml` for the published navigation source
- `packages/` for the package split this page is introducing
- `docs/` for the handbook entry pages that route readers into the repository
- `packages/bijux-canon-dev/src/bijux_canon_dev/docs/repository_docs_catalog.py` for the catalog tooling behind the handbook structure

## First Proof Check

Start with `packages/` if the main question is package ownership. Start with
`mkdocs.yml` if the main question is documentation routing. Start with
`Makefile`, `makes/`, or `.github/workflows/` if the claim is about shared
verification or release behavior. If none of those surfaces can support the
claim quickly, the docs should be treated as orientation rather than proof.

## How The Packages Split

Ingest turns source material into deterministic preparation output. Index owns
retrieval behavior and provenance-rich search results. Reason owns claims,
verification, and evidence-aware conclusions. Agent owns orchestration and
trace-backed multi-step workflows. Runtime owns acceptance, replay, and
durable execution. Stay at the repository level only for shared seams, in
maintenance pages only for repository health, and in compatibility pages only
until the canonical target is clear.

## Open This Page When

- you are still deciding which handbook owns the topic
- the concern may be cross-package, maintainer-only, or legacy-only
- you want the shortest route from the site homepage to the right handbook branch

## Open A Deeper Handbook When

- one product handbook already owns the behavior you need
- the next step is a concrete interface, workflow, schema, or test surface
- the work is already known to be a legacy-name migration issue

## Root Boundary

Stay at the site root only while you are choosing the right handbook. Leave it
as soon as one package or shared handbook can answer the real question
honestly. The homepage should shorten the route to an owner, not become a
second explanation layer above the owning docs.

## Bottom Line

Open this site root when you still need the owning handbook. Once one package
clearly owns the behavior, that handbook should carry the detailed contract,
workflow, and proof.
