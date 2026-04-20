# bijux-canon-reason

<!-- bijux-canon-badges:generated:start -->
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://pypi.org/project/bijux-canon-reason/)
[![Typing: typed](https://img.shields.io/badge/typing-typed%20(PEP%20561)-0A7BBB)](https://pypi.org/project/bijux-canon-reason/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-0F766E)](https://github.com/bijux/bijux-canon/blob/main/LICENSE)
[![CI Status](https://github.com/bijux/bijux-canon/actions/workflows/verify.yml/badge.svg)](https://github.com/bijux/bijux-canon/actions/workflows/verify.yml)
[![GitHub Repository](https://img.shields.io/badge/github-bijux%2Fbijux--canon-181717?logo=github)](https://github.com/bijux/bijux-canon)

[![bijux-canon-reason](https://img.shields.io/pypi/v/bijux-canon-reason?label=reason&logo=pypi)](https://pypi.org/project/bijux-canon-reason/)
[![bijux-canon-runtime](https://img.shields.io/pypi/v/bijux-canon-runtime?label=runtime&logo=pypi)](https://pypi.org/project/bijux-canon-runtime/)
[![bijux-canon-agent](https://img.shields.io/pypi/v/bijux-canon-agent?label=agent&logo=pypi)](https://pypi.org/project/bijux-canon-agent/)
[![bijux-canon-ingest](https://img.shields.io/pypi/v/bijux-canon-ingest?label=ingest&logo=pypi)](https://pypi.org/project/bijux-canon-ingest/)
[![bijux-canon-index](https://img.shields.io/pypi/v/bijux-canon-index?label=index&logo=pypi)](https://pypi.org/project/bijux-canon-index/)
[![agentic-flows](https://img.shields.io/pypi/v/agentic-flows?label=agentic--flows&logo=pypi)](https://pypi.org/project/agentic-flows/)
[![bijux-agent](https://img.shields.io/pypi/v/bijux-agent?label=bijux--agent&logo=pypi)](https://pypi.org/project/bijux-agent/)
[![bijux-rag](https://img.shields.io/pypi/v/bijux-rag?label=bijux--rag&logo=pypi)](https://pypi.org/project/bijux-rag/)
[![bijux-rar](https://img.shields.io/pypi/v/bijux-rar?label=bijux--rar&logo=pypi)](https://pypi.org/project/bijux-rar/)
[![bijux-vex](https://img.shields.io/pypi/v/bijux-vex?label=bijux--vex&logo=pypi)](https://pypi.org/project/bijux-vex/)

[![bijux-canon-reason](https://img.shields.io/badge/reason-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-reason)
[![bijux-canon-runtime](https://img.shields.io/badge/runtime-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-runtime)
[![bijux-canon-agent](https://img.shields.io/badge/agent-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-agent)
[![bijux-canon-ingest](https://img.shields.io/badge/ingest-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-ingest)
[![bijux-canon-index](https://img.shields.io/badge/index-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-index)
[![agentic-flows](https://img.shields.io/badge/agentic--flows-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fagentic-flows)
[![bijux-agent](https://img.shields.io/badge/bijux--agent-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-agent)
[![bijux-rag](https://img.shields.io/badge/bijux--rag-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-rag)
[![bijux-rar](https://img.shields.io/badge/bijux--rar-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-rar)
[![bijux-vex](https://img.shields.io/badge/bijux--vex-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-vex)

[![bijux-canon-reason docs](https://img.shields.io/badge/docs-reason-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/bijux-canon-reason/)
[![bijux-canon-runtime docs](https://img.shields.io/badge/docs-runtime-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/bijux-canon-runtime/)
[![bijux-canon-agent docs](https://img.shields.io/badge/docs-agent-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/bijux-canon-agent/)
[![bijux-canon-ingest docs](https://img.shields.io/badge/docs-ingest-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/bijux-canon-ingest/)
[![bijux-canon-index docs](https://img.shields.io/badge/docs-index-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/bijux-canon-index/)
<!-- bijux-canon-badges:generated:end -->

`bijux-canon-reason` is the package that turns available evidence into planned
reasoning steps, structured claims, and verification outcomes. It is where
reasoning behavior is made explicit enough to inspect, test, and defend.

If you need to understand how claims are formed, how reasoning steps are
planned and executed, how evidence is used, or where verification lives, start
here. If you need runtime governance, storage, or vector execution internals,
you are outside this package's boundary.

## Legacy continuity

- compatibility package: [`bijux-rar`](https://pypi.org/project/bijux-rar/)
- legacy import root: `bijux_rar`
- legacy command: `bijux-rar`
- canonical migration guide: <https://bijux.io/bijux-canon/08-compat-packages/migration/migration-guidance/>
- retired repository target: <https://github.com/bijux/bijux-rar>

## What this package owns

- reasoning plans, claims, and evidence-aware reasoning models
- execution of reasoning steps and local tool dispatch
- verification and provenance checks that belong to reasoning itself
- package-local CLI and API boundaries

## What this package does not own

- runtime persistence, replay authority, or execution governance
- ingest and index engines
- repository tooling and release automation

## Source map

- [`src/bijux_canon_reason/planning`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-reason/src/bijux_canon_reason/planning) for planning behavior
- [`src/bijux_canon_reason/reasoning`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-reason/src/bijux_canon_reason/reasoning) for claim and reasoning semantics
- [`src/bijux_canon_reason/execution`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-reason/src/bijux_canon_reason/execution) for step execution
- [`src/bijux_canon_reason/verification`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-reason/src/bijux_canon_reason/verification) for checks and outcomes
- [`src/bijux_canon_reason/interfaces`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-reason/src/bijux_canon_reason/interfaces) and [`src/bijux_canon_reason/api`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-reason/src/bijux_canon_reason/api) for boundaries
- [`tests`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-reason/tests) for executable protection of the package contract

## Read this next

- [Package guide](https://bijux.io/bijux-canon/bijux-canon-reason/)
- [Ownership boundary](https://bijux.io/bijux-canon/bijux-canon-reason/foundation/ownership-boundary/)
- [Architecture overview](https://bijux.io/bijux-canon/bijux-canon-reason/architecture/)
- [Interface contracts](https://bijux.io/bijux-canon/bijux-canon-reason/interfaces/)
- [Compatibility packages](https://bijux.io/bijux-canon/08-compat-packages/)
- [Test strategy](https://bijux.io/bijux-canon/bijux-canon-reason/quality/test-strategy/)
- [Changelog](https://github.com/bijux/bijux-canon/blob/main/packages/bijux-canon-reason/CHANGELOG.md)

## Primary entrypoint

- console script: `bijux-canon-reason`

## Release Readiness

- upcoming release line: `0.3.6`
- package changelog: [`CHANGELOG.md`](CHANGELOG.md)
