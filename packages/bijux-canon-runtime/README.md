# bijux-canon-runtime

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://pypi.org/project/bijux-canon-runtime/)
[![Typing: typed](https://img.shields.io/badge/typing-typed%20(PEP%20561)-0A7BBB)](https://pypi.org/project/bijux-canon-runtime/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-0F766E)](https://github.com/bijux/bijux-canon/blob/main/LICENSE)
[![CI Status](https://github.com/bijux/bijux-canon/actions/workflows/ci-bijux-canon-runtime.yml/badge.svg)](https://github.com/bijux/bijux-canon/actions/workflows/ci-bijux-canon-runtime.yml)
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

`bijux-canon-runtime` is the package that decides whether and how a flow runs,
what gets recorded about that run, and how a later replay should be judged. It
is the authority layer for execution, replay, runtime persistence, and
non-determinism governance.

If you need to understand plan versus run modes, replay acceptance, trace
capture, execution-store behavior, or non-determinism policy enforcement, start
here.

## Legacy continuity

- compatibility package: [`agentic-flows`](https://pypi.org/project/agentic-flows/)
- legacy import root: `agentic_flows`
- legacy command: `agentic-flows`
- canonical migration guide: <https://bijux.io/bijux-canon/compat-packages/migration-guidance/>
- retired repository target: <https://github.com/bijux/agentic-flows>

## What this package owns

- flow execution authority
- replay and acceptability semantics
- trace capture, runtime persistence, and execution-store behavior
- package-local CLI and API boundaries

## What this package does not own

- agent composition policy
- ingest or index domain ownership
- repository tooling and release support

## Source map

- [`src/bijux_canon_runtime/model`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-runtime/src/bijux_canon_runtime/model) for durable runtime models
- [`src/bijux_canon_runtime/runtime`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-runtime/src/bijux_canon_runtime/runtime) for execution engines and lifecycle logic
- [`src/bijux_canon_runtime/application`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-runtime/src/bijux_canon_runtime/application) for orchestration and replay coordination
- [`src/bijux_canon_runtime/observability`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-runtime/src/bijux_canon_runtime/observability) for trace capture, analysis, and storage support
- [`src/bijux_canon_runtime/interfaces`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-runtime/src/bijux_canon_runtime/interfaces) and [`src/bijux_canon_runtime/api`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-runtime/src/bijux_canon_runtime/api) for boundaries
- [`tests`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-runtime/tests) and [`examples`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-runtime/examples) for executable expectations and teaching material

## Read this next

- [Package guide](https://bijux.io/bijux-canon/bijux-canon-runtime/)
- [Architecture](https://github.com/bijux/bijux-canon/blob/main/packages/bijux-canon-runtime/docs/ARCHITECTURE.md)
- [Boundaries](https://github.com/bijux/bijux-canon/blob/main/packages/bijux-canon-runtime/docs/BOUNDARIES.md)
- [Contracts](https://github.com/bijux/bijux-canon/blob/main/packages/bijux-canon-runtime/docs/CONTRACTS.md)
- [Compatibility packages](https://bijux.io/bijux-canon/compat-packages/)
- [Changelog](https://github.com/bijux/bijux-canon/blob/main/packages/bijux-canon-runtime/CHANGELOG.md)

## Primary entrypoint

- console script: `bijux-canon-runtime`
