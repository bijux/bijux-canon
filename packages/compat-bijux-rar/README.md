# bijux-rar

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://pypi.org/project/bijux-rar/)
[![Typing: typed](https://img.shields.io/badge/typing-typed%20(PEP%20561)-0A7BBB)](https://pypi.org/project/bijux-rar/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-0F766E)](https://github.com/bijux/bijux-canon/blob/main/LICENSE)
[![CI Status](https://github.com/bijux/bijux-canon/actions/workflows/ci-bijux-canon-reason.yml/badge.svg)](https://github.com/bijux/bijux-canon/actions/workflows/ci-bijux-canon-reason.yml)
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

`bijux-rar` is the continuation of the published `bijux-rar` distribution on
PyPI. Each release keeps the legacy distribution, import, and command surfaces
available while installing `bijux-canon-reason` at the same version.

## Migration note

- new installs should use `pip install bijux-canon-reason`
- existing automation can stay on `bijux-rar` while you update imports and commands
- canonical migration guide: <https://bijux.io/bijux-canon/compat-packages/migration-guidance/>
- retired repository target: <https://github.com/bijux/bijux-rar>

## Publication status

- published continuation of the legacy `bijux-rar` distribution
- each release depends on `bijux-canon-reason==<same version>`
- intended for existing environments that still rely on the legacy name

## Canonical package

- distribution: `bijux-canon-reason`
- Python import: `bijux_canon_reason`
- command: `bijux-canon-reason`

## What this compatibility package preserves

- the legacy distribution name `bijux-rar`
- the legacy Python import surface `bijux_rar`
- the legacy command name `bijux-rar` via the canonical package

## Read this next

Use `bijux-canon-reason` directly:

- package directory: <https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-reason>
- package docs: <https://bijux.io/bijux-canon/bijux-canon-reason/>
- migration guide: <https://bijux.io/bijux-canon/compat-packages/migration-guidance/>
- changelog: <https://github.com/bijux/bijux-canon/blob/main/packages/compat-bijux-rar/CHANGELOG.md>

## Primary entrypoint

- console script: `bijux-rar`

## Package contents

- <https://github.com/bijux/bijux-canon/blob/main/packages/compat-bijux-rar/pyproject.toml>
- <https://github.com/bijux/bijux-canon/blob/main/packages/compat-bijux-rar/hatch_build.py>
- <https://github.com/bijux/bijux-canon/blob/main/packages/compat-bijux-rar/overview.md>
- <https://github.com/bijux/bijux-canon/blob/main/packages/compat-bijux-rar/CHANGELOG.md>
