# Bijux Canon Runtime
<a id="top"></a>

**A deterministic, contract-first execution and replay framework** — strict invariants, reproducible runs, and traceable outputs. Build audit-ready agent workflows with stable artifacts and replayable traces.

Canonical package name: `bijux-canon-runtime`  

[![PyPI - Version](https://img.shields.io/pypi/v/bijux-canon-runtime.svg)](https://pypi.org/project/bijux-canon-runtime/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://pypi.org/project/bijux-canon-runtime/)
[![Typing: typed (PEP 561)](https://img.shields.io/badge/typing-typed-4F8CC9.svg)](https://peps.python.org/pep-0561/)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/bijux/bijux-canon/blob/main/LICENSE)
[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-brightgreen)](https://bijux.github.io/bijux-canon-runtime/)

> **At a glance:** deterministic execution • invariant enforcement • replayable traces • CLI surface • API schema only • structured telemetry  
> **Quality:** coverage floors enforced per module, benchmark regression gate active, docs linted and built in CI, no telemetry.

---

## Table of Contents

* [Why Bijux Canon Runtime?](#why-bijux-canon-runtime)
* [Try It in 20 Seconds](#try-it-in-20-seconds)
* [Key Features](#key-features)
* [Installation](#installation)
* [Quick Start](#quick-start)
* [Artifacts & Reproducibility](#artifacts--reproducibility)
* [API Surface](#api-surface)
* [Built-in Commands](#built-in-commands)
* [Tests & Quality](#tests--quality)
* [Project Tree](#project-tree)
* [Docs & Resources](#docs--resources)
* [Contributing](#contributing)
* [License](#license)



---

<a id="why-bijux-canon-runtime"></a>
## Why Bijux Canon Runtime?

Most agent tooling optimizes for velocity. Bijux Canon Runtime prioritizes **repeatability, traceability, and audit-ready execution**:

* **Determinism first** for reliable experiments and CI validation.
* **Invariant enforcement** with fail-fast execution semantics.
* **Replayable traces** for deterministic verification.
* **Clear boundaries** between execution, retrieval, and verification.



---

<a id="try-it-in-20-seconds"></a>
## Try It in 20 Seconds

```bash
pipx install bijux-canon-runtime  # Or: pip install bijux-canon-runtime
bijux-canon-runtime --help
bijux-canon-runtime plan path/to/manifest.json
```



---

<a id="key-features"></a>
## Key Features

* **Deterministic execution** — reproducible runs with explicit budgets.
* **Contract-first design** — schema and invariants enforced at boundaries.
* **Replayable traces** — audit-grade execution records.
* **Dual surface** — CLI and API share the same contracts.
* **Structured telemetry** — correlation IDs and traceable events.



---

<a id="installation"></a>
## Installation

Requires **Python 3.11+**.

```bash
# Isolated install (recommended)
pipx install bijux-canon-runtime

# Standard
pip install bijux-canon-runtime
```

Install with `bijux-canon-runtime`; that is the supported distribution name.

Upgrade: `pipx upgrade bijux-canon-runtime` or `pip install --upgrade bijux-canon-runtime`.



---

<a id="quick-start"></a>
## Quick Start

```bash
# Discover commands/flags
bijux-canon-runtime --help

# Plan a flow from a manifest
bijux-canon-runtime plan path/to/manifest.json

# Run a deterministic execution
bijux-canon-runtime run path/to/manifest.json --db-path /tmp/execution.duckdb
```



---

<a id="artifacts--reproducibility"></a>
## Artifacts & Reproducibility

Artifacts are immutable and hash-addressed. Replaying a run verifies hashes before returning outputs.

```bash
bijux-canon-runtime diff run <run_a> <run_b> --tenant-id <tenant> --db-path /tmp/execution.duckdb
```

Docs: [Execution Lifecycle](https://bijux.github.io/bijux-canon-runtime/architecture/execution_lifecycle/) · [Invariants](https://bijux.github.io/bijux-canon-runtime/architecture/invariants/)



---

<a id="api-surface"></a>
## API Surface

The HTTP API exposes the same contracts as the CLI.

Docs: [API Overview](https://bijux.github.io/bijux-canon-runtime/api/overview/) · [Schema](https://bijux.github.io/bijux-canon-runtime/api/schema/)



---

<a id="built-in-commands"></a>
## Built-in Commands

| Command | Description | Example |
| ------- | ----------- | ------- |
| `plan` | Resolve a manifest into a plan | `bijux-canon-runtime plan manifest.json` |
| `run` | Execute a flow | `bijux-canon-runtime run manifest.json --db-path /tmp/flow.duckdb` |
| `dry-run` | Trace execution without calling tools | `bijux-canon-runtime dry-run manifest.json --db-path /tmp/flow.duckdb` |
| `inspect run` | Inspect a stored run | `bijux-canon-runtime inspect run <run_id> --tenant-id <tenant> --db-path /tmp/flow.duckdb` |
| `diff run` | Compare two runs | `bijux-canon-runtime diff run <a> <b> --tenant-id <tenant> --db-path /tmp/flow.duckdb` |

Full surface: [CLI Surface](https://bijux.github.io/bijux-canon-runtime/interface/cli_surface/)



---

<a id="tests--quality"></a>
## Tests & Quality

* **Coverage floors:** enforced per module in CI.
* **Benchmarks:** regression gate on critical path.
* **Docs:** linted and built in CI.

Quick commands:

```bash
make test
make lint
make quality
```

Artifacts: Generated in CI; see GitHub Actions for logs and reports.



---

<a id="project-tree"></a>
## Project Tree

```
../../apis/bijux-canon-runtime/  # Root-managed OpenAPI schemas
../../configs/bijux-canon-runtime/  # Root-managed lint/type/security configs
docs/           # MkDocs site
../../makes/bijux-canon-runtime/  # Root-managed task modules (docs, test, lint, etc.)
../../scripts/bijux-canon-runtime/  # Root-managed helper scripts
src/bijux_canon_runtime/  # Runtime + CLI implementation
tests/          # unit / regression / e2e
```



---

<a id="docs--resources"></a>
## Docs & Resources

* **Overview**: [Project overview](https://bijux.github.io/bijux-canon-runtime/project-overview/) · [Runtime motivation](https://bijux.github.io/bijux-canon-runtime/overview/runtime-motivation/) · [Runtime scope](https://bijux.github.io/bijux-canon-runtime/overview/runtime-scope/) · [Package boundaries](https://bijux.github.io/bijux-canon-runtime/overview/package-boundaries/) · [Mental model](https://bijux.github.io/bijux-canon-runtime/overview/mental-model/) · [Minimal run](https://bijux.github.io/bijux-canon-runtime/overview/minimal-run/) · [Audience](https://bijux.github.io/bijux-canon-runtime/overview/audience/)
* **Concepts**: [Concepts index](https://bijux.github.io/bijux-canon-runtime/concepts/) · [Determinism](https://bijux.github.io/bijux-canon-runtime/concepts/determinism/) · [Failures](https://bijux.github.io/bijux-canon-runtime/concepts/failures/)
* **Execution**: [Failure paths](https://bijux.github.io/bijux-canon-runtime/execution/failure-paths/)
* **Site**: https://bijux.github.io/bijux-canon-runtime/
* **Changelog**: https://github.com/bijux/bijux-canon/blob/main/packages/bijux-canon-runtime/CHANGELOG.md
* **Repository**: https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-runtime
* **Issues**: https://github.com/bijux/bijux-canon/issues
* **Security** (private reports): https://github.com/bijux/bijux-canon/security/advisories/new
* **Artifacts**: https://bijux.github.io/bijux-canon-runtime/artifacts/



---

<a id="contributing"></a>
## Contributing

Welcome. See **[governance/contributing.md](governance/contributing.md)** for package workflow and contribution guidance.



---

<a id="license"></a>
## License

Apache License 2.0. See **[LICENSE](https://github.com/bijux/bijux-canon/blob/main/LICENSE)**.
© 2025 Bijan Mousavi <bijan@bijux.io>.
