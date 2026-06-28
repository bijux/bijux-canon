# bijux-rag

<!-- bijux-canon-badges:generated:start -->
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://pypi.org/project/bijux-rag/)
[![Typing: typed](https://img.shields.io/badge/typing-typed%20(PEP%20561)-0A7BBB)](https://pypi.org/project/bijux-rag/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-0F766E)](https://github.com/bijux/bijux-canon/blob/main/LICENSE)
[![CI Status](https://github.com/bijux/bijux-canon/actions/workflows/verify.yml/badge.svg?branch=main)](https://github.com/bijux/bijux-canon/actions/workflows/verify.yml?query=branch%3Amain)
[![GitHub Repository](https://img.shields.io/badge/github-bijux%2Fbijux--canon-181717?logo=github)](https://github.com/bijux/bijux-canon)

[![bijux-rag](https://img.shields.io/pypi/v/bijux-rag?label=bijux--rag&logo=pypi)](https://pypi.org/project/bijux-rag/)
[![bijux-canon-runtime](https://img.shields.io/pypi/v/bijux-canon-runtime?label=runtime&logo=pypi)](https://pypi.org/project/bijux-canon-runtime/)
[![bijux-canon](https://img.shields.io/pypi/v/bijux-canon?label=bijux--canon&logo=pypi)](https://pypi.org/project/bijux-canon/)
[![bijux-canon-agent](https://img.shields.io/pypi/v/bijux-canon-agent?label=agent&logo=pypi)](https://pypi.org/project/bijux-canon-agent/)
[![bijux-canon-ingest](https://img.shields.io/pypi/v/bijux-canon-ingest?label=ingest&logo=pypi)](https://pypi.org/project/bijux-canon-ingest/)
[![bijux-canon-reason](https://img.shields.io/pypi/v/bijux-canon-reason?label=reason&logo=pypi)](https://pypi.org/project/bijux-canon-reason/)
[![bijux-canon-index](https://img.shields.io/pypi/v/bijux-canon-index?label=index&logo=pypi)](https://pypi.org/project/bijux-canon-index/)
[![agentic-flows](https://img.shields.io/pypi/v/agentic-flows?label=agentic--flows&logo=pypi)](https://pypi.org/project/agentic-flows/)
[![bijux-agent](https://img.shields.io/pypi/v/bijux-agent?label=bijux--agent&logo=pypi)](https://pypi.org/project/bijux-agent/)
[![bijux-rar](https://img.shields.io/pypi/v/bijux-rar?label=bijux--rar&logo=pypi)](https://pypi.org/project/bijux-rar/)
[![bijux-vex](https://img.shields.io/pypi/v/bijux-vex?label=bijux--vex&logo=pypi)](https://pypi.org/project/bijux-vex/)

[![bijux-rag](https://img.shields.io/badge/bijux--rag-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-rag)
[![bijux-canon-runtime](https://img.shields.io/badge/runtime-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-runtime)
[![bijux-canon](https://img.shields.io/badge/bijux--canon-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon)
[![bijux-canon-agent](https://img.shields.io/badge/agent-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-agent)
[![bijux-canon-ingest](https://img.shields.io/badge/ingest-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-ingest)
[![bijux-canon-reason](https://img.shields.io/badge/reason-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-reason)
[![bijux-canon-index](https://img.shields.io/badge/index-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-index)
[![agentic-flows](https://img.shields.io/badge/agentic--flows-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fagentic-flows)
[![bijux-agent](https://img.shields.io/badge/bijux--agent-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-agent)
[![bijux-rar](https://img.shields.io/badge/bijux--rar-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-rar)
[![bijux-vex](https://img.shields.io/badge/bijux--vex-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-vex)

[![bijux-canon-runtime docs](https://img.shields.io/badge/docs-runtime-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/bijux-canon-runtime/)
[![bijux-canon-agent docs](https://img.shields.io/badge/docs-agent-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/bijux-canon-agent/)
[![bijux-canon-ingest docs](https://img.shields.io/badge/docs-ingest-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/bijux-canon-ingest/)
[![bijux-canon-reason docs](https://img.shields.io/badge/docs-reason-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/bijux-canon-reason/)
[![bijux-canon-index docs](https://img.shields.io/badge/docs-index-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/bijux-canon-index/)
<!-- bijux-canon-badges:generated:end -->

Alias distribution for `bijux-canon-ingest`.

Install this package if you need the legacy package name and CLI command while
running the same ingest behavior as `bijux-canon-ingest`.

## Install

```bash
python3.11 -m pip install bijux-rag
bijux-rag --help
```

## What It Does

- re-exports the public Python API from `bijux-canon-ingest`
- resolves legacy submodules such as `bijux_rag.interfaces.cli.entrypoint` to
  the same canonical modules used by `bijux_canon_ingest`
- dispatches the same CLI entrypoint through the legacy `bijux-rag` command
- keeps the legacy distribution installable while steering new work to
  `bijux-canon-ingest`
- avoids becoming a second home for ingest logic or release ownership

## Compatibility Contract

If this works:

```python
from bijux_canon_ingest import Ok
```

the alias package is expected to support the same import through:

```python
from bijux_rag import Ok
```

The alias package also keeps `bijux_rag.interfaces.cli.entrypoint` pointed at
the canonical ingest CLI module, while preserving the executable name
`bijux-rag`.

## Read Next

- canonical package: [bijux-canon-ingest](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-ingest)
- canonical handbook: [bijux-canon-ingest handbook](https://bijux.io/bijux-canon/bijux-canon-ingest/)
- legacy handbook: [bijux-rag alias handbook](https://bijux.io/bijux-canon/08-compat-packages/catalog/bijux-rag/)
- migration guide: [Migration guidance](https://bijux.io/bijux-canon/08-compat-packages/migration/migration-guidance/)
- retired repository: [bijux/bijux-rag](https://github.com/bijux/bijux-rag)
- changelog: [Package changelog](https://github.com/bijux/bijux-canon/blob/main/packages/compat-bijux-rag/CHANGELOG.md)
