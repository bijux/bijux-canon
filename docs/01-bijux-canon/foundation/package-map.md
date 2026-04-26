---
title: Package Map
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-04
---

# Package Map

The package map is the clearest explanation of the product idea in this
repository. Each canonical package owns a distinct part of one larger system,
and the split is the point:

- `bijux-canon-ingest` prepares deterministic material from upstream inputs
- `bijux-canon-index` executes retrieval and backend-facing vector behavior
- `bijux-canon-reason` turns evidence into inspectable reasoning outcomes
- `bijux-canon-agent` orchestrates role-based workflows and trace-backed runs
- `bijux-canon-runtime` governs execution, replay, and acceptance authority

Read that list as a sequence of responsibilities, not as branding. The
package names matter because they let the system tell the truth about where a
concern belongs when code, interfaces, and tests evolve over time.

## Visual Summary

```mermaid
flowchart LR
    repo["bijux-canon<br/>package map"]
    ingest["Ingest"]
    index["Index"]
    reason["Reason"]
    agent["Agent"]
    runtime["Runtime"]
    maintain["Maintenance"]
    compat["Compatibility"]
    repo --> ingest
    repo --> index
    repo --> reason
    repo --> agent
    repo --> runtime
    repo --> maintain
    repo --> compat
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    classDef action fill:var(--bijux-mermaid-action-fill),stroke:var(--bijux-mermaid-action-stroke),color:var(--bijux-mermaid-action-text);
    class repo page;
    class ingest,index,reason,agent,runtime positive;
    class maintain anchor;
    class compat action;
```

## Canonical Package Roles

| Package | Core role | Open it when |
| --- | --- | --- |
| `bijux-canon-ingest` | deterministic preparation of input material | the question starts with source material, chunking, or ingest-local safeguards |
| `bijux-canon-index` | retrieval execution and provenance-rich result handling | you are reviewing vector behavior, backends, or replay-aware retrieval output |
| `bijux-canon-reason` | evidence-aware reasoning, claims, and verification | you need to inspect how evidence becomes inspectable conclusions |
| `bijux-canon-agent` | role-based orchestration and trace-backed workflow control | the question is about agent coordination rather than one local reasoning step |
| `bijux-canon-runtime` | governed execution, replay, persistence, and final acceptability | you need the authority layer that decides whether a run is acceptable and durable |

The canonical packages each own a distinct slice of the overall system:

- `bijux-canon-ingest` for deterministic document ingestion, chunking, retrieval assembly, and ingest-facing boundaries.
- `bijux-canon-index` for contract-driven vector execution with replay-aware determinism, audited backend behavior, and provenance-rich result handling.
- `bijux-canon-reason` for deterministic evidence-aware reasoning, claim formation, verification, and traceable reasoning workflows.
- `bijux-canon-agent` for deterministic, auditable agent orchestration with role-local behavior, pipeline control, and trace-backed results.
- `bijux-canon-runtime` for governed execution and replay authority with auditable non-determinism handling, persistence, and package-to-package coordination.

## Shared Maintainer Packages

- `https://bijux.io/bijux-canon/07-bijux-canon-maintain/` for repository
  automation, schema drift checks, SBOM support, and quality gates
- `https://bijux.io/bijux-canon/08-compat-packages/` for legacy distribution
  and import preservation

## Concrete Anchors

- `pyproject.toml` for workspace metadata and commit conventions
- `Makefile` and `makes/` for root automation
- `apis/` and `.github/workflows/` for schema and validation review

## Open This Page When

- you are dealing with repository-wide seams rather than one package alone
- you need shared workflow, schema, or governance context before changing code
- you want the monorepo view that sits above the package handbooks

## Decision Rule

Use this page when the main question is which package owns a responsibility. If
the answer depends mostly on one package's local behavior, continue in that
package handbook instead of keeping the question at the repository root.

## What This Page Answers

- which canonical package owns a responsibility
- which shared sections exist for maintenance and compatibility work
- how repository mapping differs from package-local ownership

## Reviewer Lens

- compare the page claims with the real root files, workflows, or schema assets
- check that repository guidance still stops where package ownership begins
- confirm that any repository rule described here is still enforceable in code or automation

## Honesty Boundary

This map routes readers to the right owner, but package-local docs, code,
schemas, and tests still provide the detailed proof.

## Next Checks

- open the owning package docs when the question stops being repository-wide
- check root files, schemas, or workflows named here before trusting prose alone
- use the maintainer handbook at `https://bijux.io/bijux-canon/07-bijux-canon-maintain/`
  when the issue is really about automation or drift tooling

