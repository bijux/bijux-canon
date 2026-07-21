# bijux-agent

<!-- bijux-canon-badges:generated:start -->
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://pypi.org/project/bijux-agent/)
[![Typing: typed](https://img.shields.io/badge/typing-typed%20(PEP%20561)-0A7BBB)](https://pypi.org/project/bijux-agent/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-0F766E)](https://github.com/bijux/bijux-canon/blob/main/LICENSE)
[![CI Status](https://github.com/bijux/bijux-canon/actions/workflows/verify.yml/badge.svg?branch=main)](https://github.com/bijux/bijux-canon/actions/workflows/verify.yml?query=branch%3Amain)
[![GitHub Repository](https://img.shields.io/badge/github-bijux%2Fbijux--canon-181717?logo=github)](https://github.com/bijux/bijux-canon)

[![bijux-agent](https://img.shields.io/pypi/v/bijux-agent?label=bijux--agent&logo=pypi)](https://pypi.org/project/bijux-agent/)
[![bijux-canon-runtime](https://img.shields.io/pypi/v/bijux-canon-runtime?label=runtime&logo=pypi)](https://pypi.org/project/bijux-canon-runtime/)
[![bijux-canon](https://img.shields.io/pypi/v/bijux-canon?label=bijux--canon&logo=pypi)](https://pypi.org/project/bijux-canon/)
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
[![bijux-canon](https://img.shields.io/badge/bijux--canon-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon)
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

`bijux-agent` preserves an earlier distribution, import root, and command for
[`bijux-canon-agent`](../bijux-canon-agent/README.md). It lets existing agent
integrations keep their established identities while orchestration behavior,
policy, traces, and releases remain owned by the canonical package.

The bridge adds no scheduler, provider adapter, convergence policy, lifecycle
event, or trace format of its own.

## Install

```bash
python3.11 -m pip install bijux-agent
bijux-agent --help
python3.11 -m bijux_agent --help
```

The built wheel requires `bijux-canon-agent` at exactly the same release as the
bridge, so compatibility cannot silently span different agent contracts.

## Identity Map

| Consumer surface | Preserved identity | Canonical identity |
| --- | --- | --- |
| distribution | `bijux-agent` | `bijux-canon-agent` |
| Python package | `bijux_agent` | `bijux_canon_agent` |
| console command | `bijux-agent` | `bijux-canon-agent` |
| module execution | `python -m bijux_agent` | `python -m bijux_canon_agent` |
| CLI module | `bijux_agent.interfaces.cli.entrypoint` | `bijux_canon_agent.interfaces.cli.entrypoint` |
| representative contract | `bijux_agent.contracts.execution_plan.ExecutionPlan` | `bijux_canon_agent.contracts.execution_plan.ExecutionPlan` |

```mermaid
flowchart LR
    integration["existing agent integration"]
    bridge["bijux-agent bridge"]
    imports["bijux_agent imports"]
    command["bijux-agent command"]
    agent["bijux-canon-agent"]

    integration --> bridge -->|"exact release pin"| agent
    integration --> imports -->|"canonical module objects"| agent
    integration --> command -->|"canonical CLI"| agent
```

## Agent Semantics

The compatibility root mirrors the canonical package's declared `__all__` and
forwards attribute access. Nested aliases resolve to the same canonical module
objects, so an `ExecutionPlan` imported through either root is the same class.
That protects type checks, dependency-injection registries, and serializers
when both names coexist during migration.

The executable and module entrypoint call the canonical agent CLI directly.
The bridge does not rewrite role definitions, tool permissions, model calls,
convergence decisions, lifecycle events, output, or exit status.

## Verify A Consumer

Confirm the import boundary used by the integration:

```python
from bijux_agent.contracts.execution_plan import (
    ExecutionPlan as CompatibilityPlan,
)
from bijux_canon_agent.contracts.execution_plan import (
    ExecutionPlan as CanonicalPlan,
)

assert CompatibilityPlan is CanonicalPlan
```

```bash
bijux-agent --help
python3.11 -m bijux_agent --help
```

Then execute representative accepted and refused orchestration cases. Compare
exit status, structured results, ordered tool/model interactions, lifecycle
events, and trace artifacts. Import identity cannot validate provider
configuration, secrets, or a consumer's policy wiring.

## Migrate To Canonical Agent Ownership

New integrations should depend on `bijux-canon-agent`, import
`bijux_canon_agent`, and invoke `bijux-canon-agent`. Existing integrations
should also search beyond ordinary source imports:

1. replace distribution requirements and lock-file entries;
2. replace root and nested imports;
3. replace command calls in scripts, images, schedulers, and runbooks;
4. inspect pipeline manifests, plugin registries, dependency injection,
   provider configuration, fixtures, and serialized dotted paths;
5. compare representative successful and refused orchestration evidence; and
6. remove the bridge only after deployed consumers no longer request its
   distribution, package, or command.

Private paths from the earlier package are not promoted to permanent canonical
API by the alias mechanism.

## Read Next

- [Agent handbook](https://bijux.io/bijux-canon/05-bijux-canon-agent/)
  for orchestration behavior and evidence
- [Compatibility contract](https://bijux.io/bijux-canon/08-compat-packages/catalog/bijux-agent/)
  for preserved identity details
- [Migration guidance](https://bijux.io/bijux-canon/08-compat-packages/migration/migration-guidance/)
  for a complete consumer inventory
- [Retired repository](https://github.com/bijux/bijux-agent) for historical
  context
- [Package changelog](CHANGELOG.md) for release history
