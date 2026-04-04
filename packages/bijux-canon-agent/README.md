# bijux-canon-agent

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://pypi.org/project/bijux-canon-agent/)
[![Typing: typed](https://img.shields.io/badge/typing-typed%20(PEP%20561)-0A7BBB)](https://pypi.org/project/bijux-canon-agent/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-0F766E)](https://github.com/bijux/bijux-canon/blob/main/LICENSE)
[![CI Status](https://github.com/bijux/bijux-canon/actions/workflows/ci-bijux-canon-agent.yml/badge.svg)](https://github.com/bijux/bijux-canon/actions/workflows/ci-bijux-canon-agent.yml)
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

`bijux-canon-agent` is the package that turns a declared agent workflow into a
deterministic, inspectable execution. It is where role implementations,
pipeline coordination, trace production, and package-local operator surfaces
come together.

If you need to understand how an agent run is composed, how trace-backed output
is produced, or where agent-facing CLI and HTTP behavior lives, start here. If
you need replay governance, runtime persistence, or cross-package execution
authority, you are probably looking for `bijux-canon-runtime` instead.

## Legacy continuity

- compatibility package: [`bijux-agent`](https://pypi.org/project/bijux-agent/)
- legacy import root: `bijux_agent`
- legacy command: `bijux-agent`
- canonical migration guide: <https://bijux.io/bijux-canon/compat-packages/migration-guidance/>
- retired repository target: <https://github.com/bijux/bijux-agent>

## What this package owns

- agent role implementations and the helpers that are specific to those roles
- deterministic orchestration of the local agent pipeline
- trace-backed result artifacts that explain what happened during a run
- package-local CLI and HTTP boundaries for invoking agent workflows

## What this package does not own

- runtime-wide persistence, replay acceptance, or execution governance
- ingest and index engines that belong to other package boundaries
- repository tooling, release automation, or root-level quality workflows

## Source map

- [`src/bijux_canon_agent/agents`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-agent/src/bijux_canon_agent/agents) for role-local behavior
- [`src/bijux_canon_agent/pipeline`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-agent/src/bijux_canon_agent/pipeline) for execution flow
- [`src/bijux_canon_agent/application`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-agent/src/bijux_canon_agent/application) for orchestration policies
- [`src/bijux_canon_agent/interfaces`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-agent/src/bijux_canon_agent/interfaces) for CLI and HTTP edges
- [`src/bijux_canon_agent/traces`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-agent/src/bijux_canon_agent/traces) for durable trace-facing models
- [`tests`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-agent/tests) for executable package truth

## Read this next

- [Package guide](https://bijux.io/bijux-canon/bijux-canon-agent/)
- [Architecture](https://github.com/bijux/bijux-canon/blob/main/packages/bijux-canon-agent/docs/ARCHITECTURE.md)
- [Boundaries](https://github.com/bijux/bijux-canon/blob/main/packages/bijux-canon-agent/docs/BOUNDARIES.md)
- [Contracts](https://github.com/bijux/bijux-canon/blob/main/packages/bijux-canon-agent/docs/CONTRACTS.md)
- [Compatibility packages](https://bijux.io/bijux-canon/compat-packages/)
- [Changelog](https://github.com/bijux/bijux-canon/blob/main/packages/bijux-canon-agent/CHANGELOG.md)

## Primary entrypoint

- console script: `bijux-canon-agent`
