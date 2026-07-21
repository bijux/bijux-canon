# bijux-canon

<!-- bijux-canon-badges:generated:start -->
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://pypi.org/project/bijux-canon/)
[![Typing: typed](https://img.shields.io/badge/typing-typed%20(PEP%20561)-0A7BBB)](https://pypi.org/project/bijux-canon/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-0F766E)](https://github.com/bijux/bijux-canon/blob/main/LICENSE)
[![CI Status](https://github.com/bijux/bijux-canon/actions/workflows/verify.yml/badge.svg?branch=main)](https://github.com/bijux/bijux-canon/actions/workflows/verify.yml?query=branch%3Amain)
[![GitHub Repository](https://img.shields.io/badge/github-bijux%2Fbijux--canon-181717?logo=github)](https://github.com/bijux/bijux-canon)

[![bijux-canon](https://img.shields.io/pypi/v/bijux-canon?label=bijux--canon&logo=pypi)](https://pypi.org/project/bijux-canon/)
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

[![bijux-canon](https://img.shields.io/badge/bijux--canon-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon)
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

[![bijux-canon-runtime docs](https://img.shields.io/badge/docs-runtime-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/06-bijux-canon-runtime/)
[![bijux-canon-agent docs](https://img.shields.io/badge/docs-agent-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/05-bijux-canon-agent/)
[![bijux-canon-ingest docs](https://img.shields.io/badge/docs-ingest-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/02-bijux-canon-ingest/)
[![bijux-canon-reason docs](https://img.shields.io/badge/docs-reason-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/04-bijux-canon-reason/)
[![bijux-canon-index docs](https://img.shields.io/badge/docs-index-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/03-bijux-canon-index/)
<!-- bijux-canon-badges:generated:end -->

`bijux-canon` is the short-name compatibility distribution for
[`bijux-canon-runtime`](../bijux-canon-runtime/README.md). It keeps established
dependency declarations, `bijux_canon` imports, and the `bijux-canon` command
working while all runtime behavior remains owned by the canonical package.

This is a runtime bridge, not an umbrella installation for the full Bijux
Canon family. Ingest, index, reason, and agent remain separately installable
packages with independent public contracts.

## Install

```bash
python3.11 -m pip install bijux-canon
bijux-canon --help
python3.11 -m bijux_canon --help
```

The bridge and canonical runtime are released together. The built
`bijux-canon` wheel requires `bijux-canon-runtime` at the exact same version,
preventing an alias release from silently forwarding into a different runtime
contract.

## Identity Map

| Consumer surface | Compatibility identity | Canonical identity |
| --- | --- | --- |
| distribution | `bijux-canon` | `bijux-canon-runtime` |
| Python package | `bijux_canon` | `bijux_canon_runtime` |
| console command | `bijux-canon` | `bijux-canon-runtime` |
| module execution | `python -m bijux_canon` | `python -m bijux_canon_runtime` |
| CLI module | `bijux_canon.interfaces.cli.entrypoint` | `bijux_canon_runtime.interfaces.cli.entrypoint` |
| representative model | `bijux_canon.model.flows.manifest.FlowManifest` | `bijux_canon_runtime.model.flows.manifest.FlowManifest` |

```mermaid
flowchart LR
    consumer["existing consumer"]
    dependency["bijux-canon distribution"]
    facade["bijux_canon import facade"]
    command["bijux-canon command"]
    runtime["bijux-canon-runtime"]

    consumer --> dependency
    dependency -->|"exact release pin"| runtime
    consumer --> facade -->|"public exports and module aliases"| runtime
    consumer --> command -->|"canonical CLI entrypoint"| runtime
```

## Runtime Semantics

The package root exposes the canonical runtime's declared `__all__` and
forwards attribute access without eagerly importing execution or persistence
internals. Non-local `bijux_canon.*` imports are resolved against the matching
`bijux_canon_runtime.*` path. A nested class imported through either name is
therefore the same Python object, which protects `isinstance` checks,
registries, and serializers from duplicate class identities.

The compatibility command and `python -m bijux_canon` call the canonical CLI.
They do not translate arguments, configuration, exit codes, or artifacts.
Runtime admission, execution, persistence, resume, and replay consequently
have one implementation and one documentation authority.

## Verify A Consumer

Exercise the surfaces that the application actually depends on:

```python
from bijux_canon import FlowManifest as CompatibilityManifest
from bijux_canon_runtime import FlowManifest as CanonicalManifest

assert CompatibilityManifest is CanonicalManifest
```

```bash
bijux-canon --help
bijux-canon --version
python3.11 -m bijux_canon --help
```

For a real workflow, compare exit status, structured output, artifact layout,
and replay behavior under the compatibility and canonical commands. Matching
imports alone do not validate a deployment's providers, secrets, storage, or
historical run data.

## Migrate To The Canonical Name

New applications should depend on `bijux-canon-runtime`, import
`bijux_canon_runtime`, and invoke `bijux-canon-runtime`. Existing applications
can migrate one boundary at a time:

1. Replace the distribution requirement and lock-file entry.
2. Replace root and nested Python imports.
3. Replace shell commands, container entrypoints, and automation.
4. Search configuration and serialized metadata for dotted `bijux_canon.*`
   paths.
5. Run representative workflows and compare their artifacts and replay
   results.
6. Remove the bridge only after deployed consumers no longer load its
   distribution, module, or command identities.

The bridge intentionally does not promise every private runtime module as a
permanent API. Depend on documented canonical exports wherever possible.

## Read Next

- [Runtime handbook](https://bijux.io/bijux-canon/06-bijux-canon-runtime/)
  for execution, artifacts, resume, and replay semantics
- [Compatibility contract](https://bijux.io/bijux-canon/08-compat-packages/catalog/bijux-canon/)
  for the complete preserved-identity boundary
- [Migration guidance](https://bijux.io/bijux-canon/08-compat-packages/migration/migration-guidance/)
  for consumer inventory and validation
- [Package changelog](CHANGELOG.md) for release history
