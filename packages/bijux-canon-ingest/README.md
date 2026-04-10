# bijux-canon-ingest

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://pypi.org/project/bijux-canon-ingest/)
[![Typing: typed](https://img.shields.io/badge/typing-typed%20(PEP%20561)-0A7BBB)](https://pypi.org/project/bijux-canon-ingest/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-0F766E)](https://github.com/bijux/bijux-canon/blob/main/LICENSE)
[![CI Status](https://github.com/bijux/bijux-canon/actions/workflows/verify.yml/badge.svg)](https://github.com/bijux/bijux-canon/actions/workflows/verify.yml)
[![GitHub Repository](https://img.shields.io/badge/github-bijux%2Fbijux--canon-181717?logo=github)](https://github.com/bijux/bijux-canon)

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

`bijux-canon-ingest` is the package that turns raw documents into deterministic
ingest artifacts and retrieval-ready structures. It is where cleaning,
chunking, package-local retrieval assembly, and ingest-facing boundaries live.

This package should help a maintainer answer practical questions such as:

- how does a source document become stable ingest output
- where do retrieval-oriented assembly steps belong
- which code is pure transformation logic and which code is adapter work

## Legacy continuity

- compatibility package: [`bijux-rag`](https://pypi.org/project/bijux-rag/)
- legacy import root: `bijux_rag`
- legacy command: `bijux-rag`
- canonical migration guide: <https://bijux.io/bijux-canon/compat-packages/migration/migration-guidance/>
- retired repository target: <https://github.com/bijux/bijux-rag>

## What this package owns

- document cleaning, normalization, and chunking
- ingest-local retrieval and indexing assembly
- package-local CLI and HTTP boundaries
- ingest-specific adapters, safeguards, and observability helpers

## What this package does not own

- standalone vector execution semantics
- runtime-wide governance, persistence, or replay authority
- repository tooling and release automation

## Source map

- [`src/bijux_canon_ingest/processing`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-ingest/src/bijux_canon_ingest/processing) for deterministic document transforms
- [`src/bijux_canon_ingest/retrieval`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-ingest/src/bijux_canon_ingest/retrieval) for retrieval-oriented models and assembly
- [`src/bijux_canon_ingest/application`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-ingest/src/bijux_canon_ingest/application) for package workflows
- [`src/bijux_canon_ingest/infra`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-ingest/src/bijux_canon_ingest/infra) and [`src/bijux_canon_ingest/integrations`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-ingest/src/bijux_canon_ingest/integrations) for adapters
- [`src/bijux_canon_ingest/interfaces`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-ingest/src/bijux_canon_ingest/interfaces) for CLI and HTTP edges
- [`tests`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-ingest/tests) for behavior, layout, and corpus-backed checks

## Read this next

- [Package guide](https://bijux.io/bijux-canon/bijux-canon-ingest/)
- [Package overview](https://bijux.io/bijux-canon/bijux-canon-ingest/foundation/package-overview/)
- [Ownership boundary](https://bijux.io/bijux-canon/bijux-canon-ingest/foundation/ownership-boundary/)
- [Architecture overview](https://bijux.io/bijux-canon/bijux-canon-ingest/architecture/)
- [Operator workflows](https://bijux.io/bijux-canon/bijux-canon-ingest/interfaces/operator-workflows/)
- [Compatibility packages](https://bijux.io/bijux-canon/compat-packages/)
- [Changelog](https://github.com/bijux/bijux-canon/blob/main/packages/bijux-canon-ingest/CHANGELOG.md)

## Primary entrypoint

- console script: `bijux-canon-ingest`
