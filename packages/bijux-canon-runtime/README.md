# bijux-canon-runtime

<!-- bijux-canon-badges:generated:start -->
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://pypi.org/project/bijux-canon-runtime/)
[![Typing: typed](https://img.shields.io/badge/typing-typed%20(PEP%20561)-0A7BBB)](https://pypi.org/project/bijux-canon-runtime/)
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
- canonical migration guide: <https://bijux.io/bijux-canon/08-compat-packages/migration/migration-guidance/>
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

- [`src/bijux_canon_runtime/model`](https://github.com/bijux/bijux-canon/tree/main/packages/06-bijux-canon-runtime/src/bijux_canon_runtime/model) for durable runtime models
- [`src/bijux_canon_runtime/runtime`](https://github.com/bijux/bijux-canon/tree/main/packages/06-bijux-canon-runtime/src/bijux_canon_runtime/runtime) for execution engines and lifecycle logic
- [`src/bijux_canon_runtime/application`](https://github.com/bijux/bijux-canon/tree/main/packages/06-bijux-canon-runtime/src/bijux_canon_runtime/application) for orchestration and replay coordination
- [`src/bijux_canon_runtime/observability`](https://github.com/bijux/bijux-canon/tree/main/packages/06-bijux-canon-runtime/src/bijux_canon_runtime/observability) for trace capture, analysis, and storage support
- [`src/bijux_canon_runtime/interfaces`](https://github.com/bijux/bijux-canon/tree/main/packages/06-bijux-canon-runtime/src/bijux_canon_runtime/interfaces) and [`src/bijux_canon_runtime/api`](https://github.com/bijux/bijux-canon/tree/main/packages/06-bijux-canon-runtime/src/bijux_canon_runtime/api) for boundaries
- [`tests`](https://github.com/bijux/bijux-canon/tree/main/packages/06-bijux-canon-runtime/tests) and [`examples`](https://github.com/bijux/bijux-canon/tree/main/packages/06-bijux-canon-runtime/examples) for executable expectations and teaching material

## Read this next

- [Package guide](https://bijux.io/bijux-canon/06-bijux-canon-runtime/)
- [Ownership boundary](https://bijux.io/bijux-canon/06-bijux-canon-runtime/foundation/ownership-boundary/)
- [Architecture overview](https://bijux.io/bijux-canon/06-bijux-canon-runtime/architecture/)
- [Interface contracts](https://bijux.io/bijux-canon/06-bijux-canon-runtime/interfaces/)
- [Release and versioning](https://bijux.io/bijux-canon/06-bijux-canon-runtime/operations/release-and-versioning/)
- [Compatibility packages](https://bijux.io/bijux-canon/08-compat-packages/)
- [Changelog](https://github.com/bijux/bijux-canon/blob/main/packages/06-bijux-canon-runtime/CHANGELOG.md)

## Primary entrypoint

- console script: `bijux-canon-runtime`
