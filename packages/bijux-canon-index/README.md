# bijux-canon-index

<!-- bijux-canon-badges:generated:start -->
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://pypi.org/project/bijux-canon-index/)
[![Typing: typed](https://img.shields.io/badge/typing-typed%20(PEP%20561)-0A7BBB)](https://pypi.org/project/bijux-canon-index/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-0F766E)](https://github.com/bijux/bijux-canon/blob/main/LICENSE)
[![CI Status](https://github.com/bijux/bijux-canon/actions/workflows/verify.yml/badge.svg)](https://github.com/bijux/bijux-canon/actions/workflows/verify.yml)
[![GitHub Repository](https://img.shields.io/badge/github-bijux%2Fbijux--canon-181717?logo=github)](https://github.com/bijux/bijux-canon)
[![bijux-canon-index](https://img.shields.io/badge/bijux--canon--index-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-index)

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

[![bijux-canon-runtime docs](https://img.shields.io/badge/docs-runtime-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/bijux-canon-runtime/)
[![bijux-canon-agent docs](https://img.shields.io/badge/docs-agent-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/bijux-canon-agent/)
[![bijux-canon-ingest docs](https://img.shields.io/badge/docs-ingest-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/bijux-canon-ingest/)
[![bijux-canon-reason docs](https://img.shields.io/badge/docs-reason-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/bijux-canon-reason/)
[![bijux-canon-index docs](https://img.shields.io/badge/docs-index-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/bijux-canon-index/)
<!-- bijux-canon-badges:generated:end -->

`bijux-canon-index` is the vector execution package in `bijux-canon`. It does
more than "run a nearest-neighbor query." It executes a declared vector
operation against a concrete backend, records enough provenance to explain the
result later, and supports replay-oriented comparison when determinism matters.

If you need to understand vector-store adapters, embedding execution,
capability profiles, replay semantics, or provenance-aware result comparison,
start here. If you need document preparation, runtime governance, or repository
tooling, you are outside this package's boundary.

## Legacy continuity

- compatibility package: [`bijux-vex`](https://pypi.org/project/bijux-vex/)
- legacy import root: `bijux_vex`
- legacy command: `bijux-vex`
- canonical migration guide: <https://bijux.io/bijux-canon/compat-packages/migration/migration-guidance/>
- retired repository target: <https://github.com/bijux/bijux-vex>

## What this package owns

- vector execution semantics and backend orchestration
- provenance-aware result artifacts and replay-oriented comparison
- plugin-backed vector store, embedding, and runner integration
- package-local HTTP behavior and related schemas

## What this package does not own

- document ingestion and normalization
- runtime-wide authority, persistence, or replay policy
- repository maintenance automation

## Source map

- [`src/bijux_canon_index/core`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-index/src/bijux_canon_index/core) for stable primitives and errors
- [`src/bijux_canon_index/domain`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-index/src/bijux_canon_index/domain) for execution and provenance semantics
- [`src/bijux_canon_index/application`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-index/src/bijux_canon_index/application) for package workflows
- [`src/bijux_canon_index/infra`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-index/src/bijux_canon_index/infra) for backends, adapters, and plugins
- [`src/bijux_canon_index/interfaces`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-index/src/bijux_canon_index/interfaces) and [`src/bijux_canon_index/api`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-index/src/bijux_canon_index/api) for boundaries
- [`plugins`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-index/plugins) for plugin development support
- [`tests`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-index/tests) for conformance and replay protection

## Read this next

- [Package guide](https://bijux.io/bijux-canon/bijux-canon-index/)
- [Architecture overview](https://bijux.io/bijux-canon/bijux-canon-index/architecture/)
- [API surface](https://bijux.io/bijux-canon/bijux-canon-index/interfaces/api-surface/)
- [Execution model](https://bijux.io/bijux-canon/bijux-canon-index/architecture/execution-model/)
- [Error model](https://bijux.io/bijux-canon/bijux-canon-index/architecture/error-model/)
- [Changelog](https://github.com/bijux/bijux-canon/blob/main/packages/bijux-canon-index/CHANGELOG.md)

## Primary entrypoint

- console script: `bijux-canon-index`
