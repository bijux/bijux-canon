# bijux-canon-index

<!-- bijux-canon-badges:generated:start -->
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://pypi.org/project/bijux-canon-index/)
[![Typing: typed](https://img.shields.io/badge/typing-typed%20(PEP%20561)-0A7BBB)](https://pypi.org/project/bijux-canon-index/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-0F766E)](https://github.com/bijux/bijux-canon/blob/main/LICENSE)
[![CI Status](https://github.com/bijux/bijux-canon/actions/workflows/verify.yml/badge.svg?branch=main)](https://github.com/bijux/bijux-canon/actions/workflows/verify.yml?query=branch%3Amain)
[![GitHub Repository](https://img.shields.io/badge/github-bijux%2Fbijux--canon-181717?logo=github)](https://github.com/bijux/bijux-canon)

[![bijux-canon-index](https://img.shields.io/pypi/v/bijux-canon-index?label=index&logo=pypi)](https://pypi.org/project/bijux-canon-index/)
[![bijux-canon-runtime](https://img.shields.io/pypi/v/bijux-canon-runtime?label=runtime&logo=pypi)](https://pypi.org/project/bijux-canon-runtime/)
[![bijux-canon](https://img.shields.io/pypi/v/bijux-canon?label=bijux--canon&logo=pypi)](https://pypi.org/project/bijux-canon/)
[![bijux-canon-agent](https://img.shields.io/pypi/v/bijux-canon-agent?label=agent&logo=pypi)](https://pypi.org/project/bijux-canon-agent/)
[![bijux-canon-ingest](https://img.shields.io/pypi/v/bijux-canon-ingest?label=ingest&logo=pypi)](https://pypi.org/project/bijux-canon-ingest/)
[![bijux-canon-reason](https://img.shields.io/pypi/v/bijux-canon-reason?label=reason&logo=pypi)](https://pypi.org/project/bijux-canon-reason/)
[![agentic-flows](https://img.shields.io/pypi/v/agentic-flows?label=agentic--flows&logo=pypi)](https://pypi.org/project/agentic-flows/)
[![bijux-agent](https://img.shields.io/pypi/v/bijux-agent?label=bijux--agent&logo=pypi)](https://pypi.org/project/bijux-agent/)
[![bijux-rag](https://img.shields.io/pypi/v/bijux-rag?label=bijux--rag&logo=pypi)](https://pypi.org/project/bijux-rag/)
[![bijux-rar](https://img.shields.io/pypi/v/bijux-rar?label=bijux--rar&logo=pypi)](https://pypi.org/project/bijux-rar/)
[![bijux-vex](https://img.shields.io/pypi/v/bijux-vex?label=bijux--vex&logo=pypi)](https://pypi.org/project/bijux-vex/)

[![bijux-canon-index](https://img.shields.io/badge/index-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-index)
[![bijux-canon-runtime](https://img.shields.io/badge/runtime-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-runtime)
[![bijux-canon](https://img.shields.io/badge/bijux--canon-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon)
[![bijux-canon-agent](https://img.shields.io/badge/agent-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-agent)
[![bijux-canon-ingest](https://img.shields.io/badge/ingest-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-ingest)
[![bijux-canon-reason](https://img.shields.io/badge/reason-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-reason)
[![agentic-flows](https://img.shields.io/badge/agentic--flows-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fagentic-flows)
[![bijux-agent](https://img.shields.io/badge/bijux--agent-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-agent)
[![bijux-rag](https://img.shields.io/badge/bijux--rag-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-rag)
[![bijux-rar](https://img.shields.io/badge/bijux--rar-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-rar)
[![bijux-vex](https://img.shields.io/badge/bijux--vex-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-vex)

[![bijux-canon-index docs](https://img.shields.io/badge/docs-index-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/03-bijux-canon-index/)
[![bijux-canon-runtime docs](https://img.shields.io/badge/docs-runtime-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/06-bijux-canon-runtime/)
[![bijux-canon-agent docs](https://img.shields.io/badge/docs-agent-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/05-bijux-canon-agent/)
[![bijux-canon-ingest docs](https://img.shields.io/badge/docs-ingest-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/02-bijux-canon-ingest/)
[![bijux-canon-reason docs](https://img.shields.io/badge/docs-reason-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/04-bijux-canon-reason/)
<!-- bijux-canon-badges:generated:end -->

`bijux-canon-index` is the vector execution package in `bijux-canon`. It does
more than "run a nearest-neighbor query." It executes a declared vector
operation against a concrete backend, records enough provenance to explain the
result later, and supports replay-oriented comparison when determinism matters.

If you need to understand vector-store adapters, embedding execution,
capability profiles, replay semantics, or provenance-aware result comparison,
start here. If you need document preparation, runtime governance, or repository
tooling, you are outside this package's boundary.

## Execution Contract

Every execution combines four declarations:

| Declaration | Supported values | Effect |
| --- | --- | --- |
| execution intent | `exact_validation`, `reproducible_research`, `exploratory_search`, `production_retrieval` | records why a particular loss and replay posture is acceptable |
| execution mode | `strict`, `bounded`, `exploratory` | controls refusal, tolerance, and diagnostic behavior |
| execution contract | `deterministic`, `non_deterministic` | distinguishes exact replay claims from bounded approximation |
| execution budget | latency, memory, error, candidate, and ANN limits | constrains resource use and approximation before execution |

An `ExecutionRequest` becomes an `ExecutionPlan`, an `ExecutionSession`, an
`ExecutionResult`, and—when materialized—an `ExecutionArtifact`. Provenance
records backend and parameter identity so `explain`, `replay`, and `compare`
operate on evidence rather than inference.

```mermaid
flowchart LR
    request["request + intent"] --> plan["validated plan"]
    plan --> registry["backend registry"]
    registry --> engine["vector execution engine"]
    engine --> result["result + cost"]
    result --> artifact["artifact + provenance"]
    artifact --> replay["explain / replay / compare"]
```

## Command Surface

The repository contains a complete Typer application under
`bijux_canon_index.interfaces.cli.app`. The current package metadata does **not**
register a `bijux-canon-index` console script, so source and wheel users must
not assume that executable exists. The application can be invoked explicitly:

```bash
python -m bijux_canon_index.interfaces.cli.app capabilities
python -m bijux_canon_index.interfaces.cli.app execute \
  --vector '[0.2, 0.8]' \
  --execution-contract deterministic \
  --execution-intent exact_validation \
  --execution-mode strict
```

The missing console-script registration is a packaging limitation, not a
documentation alias. HTTP and in-process users are unaffected.

## HTTP Contract

The checked-in v1 schema exposes backend capabilities, corpus creation,
ingestion, vector execution, explanation, replay, artifact materialization,
artifact listing, and run listing. See
[`apis/bijux-canon-index/v1/schema.yaml`](../../apis/bijux-canon-index/v1/schema.yaml)
and its pinned JSON and schema hash.

## What This Package Takes And Produces

- takes: declared vector execution requests, backend capability profiles, and embedding or store adapter inputs
- produces: provenance-aware retrieval results, backend execution artifacts, replay comparison surfaces, and explicit capability failures
- guarantees: vector execution remains attached to one declared contract instead of one implicit backend assumption
- does not do: normalize source documents, own runtime persistence, or hide backend divergence behind one undifferentiated API

## Legacy continuity

- compatibility package: [`bijux-vex`](https://pypi.org/project/bijux-vex/)
- legacy import root: `bijux_vex`
- legacy command: `bijux-vex`
- canonical migration guide: [Migration guidance](https://bijux.io/bijux-canon/08-compat-packages/migration/migration-guidance/)
- retired repository target: [https://github.com/bijux/bijux-vex](https://github.com/bijux/bijux-vex) (see [Repository consolidation notes](https://bijux.io/bijux-canon/08-compat-packages/migration/repository-consolidation/))

## What this package owns

- vector execution semantics and backend orchestration
- provenance-aware result artifacts and replay-oriented comparison
- plugin-backed vector store, embedding, and runner integration
- package-local HTTP behavior and related schemas

## What this package does not own

- document ingestion and normalization
- runtime-wide authority, persistence, or replay policy
- repository maintenance automation

## Failure And Replay Semantics

- strict execution refuses unsupported capability, invalid-vector, and budget
  combinations before presenting a result as valid
- deterministic and non-deterministic runs have different support levels and
  different replay claims
- approximate runs can record witness mode, target recall, candidate limits,
  ANN parameters, low-signal policy, and an explicit non-replayable declaration
- replay can refuse changed indexes or parameters instead of silently comparing
  unlike executions
- corrupt artifacts, unavailable backends, backend divergence, and unsupported
  replay remain distinct failures

## Source map

- [`src/bijux_canon_index/core`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-index/src/bijux_canon_index/core) for stable primitives and errors
- [`src/bijux_canon_index/domain`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-index/src/bijux_canon_index/domain) for execution and provenance semantics
- [`src/bijux_canon_index/application`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-index/src/bijux_canon_index/application) for package workflows
- [`src/bijux_canon_index/infra`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-index/src/bijux_canon_index/infra) for backends, adapters, and plugins
- [`src/bijux_canon_index/interfaces`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-index/src/bijux_canon_index/interfaces) and [`src/bijux_canon_index/api`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-index/src/bijux_canon_index/api) for boundaries
- [`plugins`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-index/plugins) for plugin development support
- [`tests`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-index/tests) for conformance and replay protection

## Read this next

- [Package guide](https://bijux.io/bijux-canon/03-bijux-canon-index/)
- [Architecture overview](https://bijux.io/bijux-canon/03-bijux-canon-index/architecture/)
- [API surface](https://bijux.io/bijux-canon/03-bijux-canon-index/interfaces/api-surface/)
- [Execution model](https://bijux.io/bijux-canon/03-bijux-canon-index/architecture/execution-model/)
- [Error model](https://bijux.io/bijux-canon/03-bijux-canon-index/architecture/error-model/)
- [Changelog](https://github.com/bijux/bijux-canon/blob/main/packages/bijux-canon-index/CHANGELOG.md)

## Entrypoints

- HTTP application and v1 OpenAPI contract
- in-process application and domain modules
- module-invoked Typer application at `bijux_canon_index.interfaces.cli.app`
- no registered console script in the current package metadata

## Release Readiness

- release line prepared for publish: `0.3.9`
- release date: `2026-07-04`
- package changelog: [`CHANGELOG.md`](CHANGELOG.md)
