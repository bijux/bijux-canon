# bijux-agent

<!-- bijux-canon-badges:generated:start -->
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://pypi.org/project/bijux-agent/)
[![Typing: typed](https://img.shields.io/badge/typing-typed%20(PEP%20561)-0A7BBB)](https://pypi.org/project/bijux-agent/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-0F766E)](https://github.com/bijux/bijux-canon/blob/main/LICENSE)
[![CI Status](https://github.com/bijux/bijux-canon/actions/workflows/verify.yml/badge.svg)](https://github.com/bijux/bijux-canon/actions/workflows/verify.yml)
[![GitHub Repository](https://img.shields.io/badge/github-bijux%2Fbijux--canon-181717?logo=github)](https://github.com/bijux/bijux-canon)

[![bijux-agent](https://img.shields.io/pypi/v/bijux-agent?label=bijux--agent&logo=pypi)](https://pypi.org/project/bijux-agent/)
[![bijux-canon-runtime](https://img.shields.io/pypi/v/bijux-canon-runtime?label=runtime&logo=pypi)](https://pypi.org/project/bijux-canon-runtime/)
[![bijux-canon-agent](https://img.shields.io/pypi/v/bijux-canon-agent?label=agent&logo=pypi)](https://pypi.org/project/bijux-canon-agent/)
[![bijux-canon-ingest](https://img.shields.io/pypi/v/bijux-canon-ingest?label=ingest&logo=pypi)](https://pypi.org/project/bijux-canon-ingest/)
[![bijux-canon-reason](https://img.shields.io/pypi/v/bijux-canon-reason?label=reason&logo=pypi)](https://pypi.org/project/bijux-canon-reason/)
[![bijux-canon-index](https://img.shields.io/pypi/v/bijux-canon-index?label=index&logo=pypi)](https://pypi.org/project/bijux-canon-index/)
[![agentic-flows](https://img.shields.io/pypi/v/agentic-flows?label=agentic--flows&logo=pypi)](https://pypi.org/project/agentic-flows/)
[![bijux-rag](https://img.shields.io/pypi/v/bijux-rag?label=bijux--rag&logo=pypi)](https://pypi.org/project/bijux-rag/)
[![bijux-rar](https://img.shields.io/pypi/v/bijux-rar?label=bijux--rar&logo=pypi)](https://pypi.org/project/bijux-rar/)
[![bijux-vex](https://img.shields.io/pypi/v/bijux-vex?label=bijux--vex&logo=pypi)](https://pypi.org/project/bijux-vex/)

[![bijux-agent](https://img.shields.io/badge/bijux--agent-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-agent)
[![bijux-canon-runtime](https://img.shields.io/badge/runtime-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-runtime)
[![bijux-canon-agent](https://img.shields.io/badge/agent-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-agent)
[![bijux-canon-ingest](https://img.shields.io/badge/ingest-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-ingest)
[![bijux-canon-reason](https://img.shields.io/badge/reason-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-reason)
[![bijux-canon-index](https://img.shields.io/badge/index-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-index)
[![agentic-flows](https://img.shields.io/badge/agentic--flows-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fagentic-flows)
[![bijux-rag](https://img.shields.io/badge/bijux--rag-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-rag)
[![bijux-rar](https://img.shields.io/badge/bijux--rar-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-rar)
[![bijux-vex](https://img.shields.io/badge/bijux--vex-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-vex)

[![bijux-canon-runtime docs](https://img.shields.io/badge/docs-runtime-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/06-bijux-canon-runtime/)
[![bijux-canon-agent docs](https://img.shields.io/badge/docs-agent-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/05-bijux-canon-agent/)
[![bijux-canon-ingest docs](https://img.shields.io/badge/docs-ingest-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/02-bijux-canon-ingest/)
[![bijux-canon-reason docs](https://img.shields.io/badge/docs-reason-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/04-bijux-canon-reason/)
[![bijux-canon-index docs](https://img.shields.io/badge/docs-index-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/03-bijux-canon-index/)
<!-- bijux-canon-badges:generated:end -->

`bijux-agent` is the continuation of the published `bijux-agent` distribution
on PyPI. Each release keeps the legacy distribution, import, and command
surfaces available while installing `bijux-canon-agent` at the same version.

Its package handbook lives at
[legacy package handbook](https://bijux.io/bijux-canon/08-compat-packages/catalog/bijux-agent/).

## Migration note

- new installs should use `uv add bijux-canon-agent`
- existing automation can stay on `bijux-agent` while you update imports and commands
- canonical migration guide: [Migration guidance](https://bijux.io/bijux-canon/08-compat-packages/migration/migration-guidance/)
- retired repository target: `bijux/bijux-agent` (see [Repository consolidation notes](https://bijux.io/bijux-canon/08-compat-packages/migration/repository-consolidation/))

## Publication status

- published continuation of the legacy `bijux-agent` distribution
- each release depends on `bijux-canon-agent==<same version>`
- intended for existing environments that still rely on the legacy name

## Canonical package

- distribution: `bijux-canon-agent`
- Python import: `bijux_canon_agent`
- command: `bijux-canon-agent`

## What this compatibility package preserves

- the legacy distribution name `bijux-agent`
- the legacy Python import surface `bijux_agent`
- the legacy command name `bijux-agent`

## Read this next

Use `bijux-canon-agent` directly:

- package directory: [Canonical package source directory](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-agent)
- legacy package handbook: [Legacy package handbook](https://bijux.io/bijux-canon/08-compat-packages/catalog/bijux-agent/)
- package docs: [Canonical package handbook](https://bijux.io/bijux-canon/05-bijux-canon-agent/)
- migration guide: [Migration guidance](https://bijux.io/bijux-canon/08-compat-packages/migration/migration-guidance/)
- changelog: [Package changelog](https://github.com/bijux/bijux-canon/blob/main/packages/compat-bijux-agent/CHANGELOG.md)

## Primary entrypoint

- console script: `bijux-agent`

## Package contents

- [`pyproject.toml`](https://github.com/bijux/bijux-canon/blob/main/packages/compat-bijux-agent/pyproject.toml)
- [`hatch_build.py`](https://github.com/bijux/bijux-canon/blob/main/packages/compat-bijux-agent/hatch_build.py)
- [`overview.md`](https://github.com/bijux/bijux-canon/blob/main/packages/compat-bijux-agent/overview.md)
- [`CHANGELOG.md`](https://github.com/bijux/bijux-canon/blob/main/packages/compat-bijux-agent/CHANGELOG.md)

## Release Readiness

- upcoming release line: `0.3.6`
- package changelog: [`CHANGELOG.md`](CHANGELOG.md)
