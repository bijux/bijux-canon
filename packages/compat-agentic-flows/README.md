# agentic-flows

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://pypi.org/project/agentic-flows/)
[![Typing: typed](https://img.shields.io/badge/typing-typed%20(PEP%20561)-0A7BBB)](https://pypi.org/project/agentic-flows/)
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

`agentic-flows` is the continuation of the published `agentic-flows`
distribution on PyPI. Each release keeps the legacy distribution, import, and
command surfaces available while installing `bijux-canon-runtime` at the same
version.

This package exists to reduce migration breakage, not to become the preferred
entrypoint for new work. Its package handbook lives at
<https://bijux.io/bijux-canon/compat-packages/agentic-flows/>.

## Migration note

- new installs should use `pip install bijux-canon-runtime`
- existing automation can stay on `agentic-flows` while you update imports and commands
- canonical migration guide: <https://bijux.io/bijux-canon/compat-packages/migration-guidance/>
- retired repository target: <https://github.com/bijux/agentic-flows>

## Publication status

- published continuation of the legacy `agentic-flows` distribution
- each release depends on `bijux-canon-runtime==<same version>`
- intended for existing environments that still rely on the legacy name

## Canonical package

- distribution: `bijux-canon-runtime`
- Python import: `bijux_canon_runtime`
- command: `bijux-canon-runtime`

## What this compatibility package preserves

- the legacy distribution name `agentic-flows`
- the legacy Python import surface `agentic_flows`
- the legacy command name `agentic-flows`

## Read this next

Depend on `bijux-canon-runtime` directly and read the canonical docs there:

- package directory: <https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-runtime>
- legacy package handbook: <https://bijux.io/bijux-canon/compat-packages/agentic-flows/>
- package docs: <https://bijux.io/bijux-canon/bijux-canon-runtime/>
- migration guide: <https://bijux.io/bijux-canon/compat-packages/migration-guidance/>
- changelog: <https://github.com/bijux/bijux-canon/blob/main/packages/compat-agentic-flows/CHANGELOG.md>

## Primary entrypoint

- console script: `agentic-flows`

## Package contents

- <https://github.com/bijux/bijux-canon/blob/main/packages/compat-agentic-flows/pyproject.toml>
- <https://github.com/bijux/bijux-canon/blob/main/packages/compat-agentic-flows/hatch_build.py>
- <https://github.com/bijux/bijux-canon/blob/main/packages/compat-agentic-flows/overview.md>
- <https://github.com/bijux/bijux-canon/blob/main/packages/compat-agentic-flows/CHANGELOG.md>
