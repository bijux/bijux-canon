# Agentic Flows
<a id="top"></a>

**A deterministic, contract-first execution and replay framework** — strict invariants, reproducible runs, and traceable outputs. Build audit-ready agent workflows with stable artifacts and replayable traces.

Canonical package name: `bijux-llm-flows`  
Legacy compatibility package: `agentic-flows`

[![PyPI - Version](https://img.shields.io/pypi/v/bijux-llm-flows.svg)](https://pypi.org/project/bijux-llm-flows/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://pypi.org/project/bijux-llm-flows/)
[![Typing: typed (PEP 561)](https://img.shields.io/badge/typing-typed-4F8CC9.svg)](https://peps.python.org/pep-0561/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/bijux/bijux-llm-nexus/blob/main/LICENSE)
[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-brightgreen)](https://bijux.github.io/agentic-flows/)

> **At a glance:** deterministic execution • invariant enforcement • replayable traces • CLI surface • API schema only • structured telemetry  
> **Quality:** coverage floors enforced per module, benchmark regression gate active, docs linted and built in CI, no telemetry.

---

## Table of Contents

* [Why Agentic Flows?](#why-agentic-flows)
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

<a id="why-agentic-flows"></a>
## Why Agentic Flows?

Most agent tooling optimizes for velocity. Agentic Flows prioritizes **repeatability, traceability, and audit-ready execution**:

* **Determinism first** for reliable experiments and CI validation.
* **Invariant enforcement** with fail-fast execution semantics.
* **Replayable traces** for deterministic verification.
* **Clear boundaries** between execution, retrieval, and verification.



---

<a id="try-it-in-20-seconds"></a>
## Try It in 20 Seconds

```bash
pipx install bijux-llm-flows  # Or: pip install bijux-llm-flows
bijux-llm-flows --help
bijux-llm-flows plan path/to/manifest.json
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
pipx install bijux-llm-flows

# Standard
pip install bijux-llm-flows
```

Legacy installs via `agentic-flows` remain supported as a compatibility package.

Upgrade: `pipx upgrade bijux-llm-flows` or `pip install --upgrade bijux-llm-flows`.



---

<a id="quick-start"></a>
## Quick Start

```bash
# Discover commands/flags
bijux-llm-flows --help

# Plan a flow from a manifest
bijux-llm-flows plan path/to/manifest.json

# Run a deterministic execution
bijux-llm-flows run path/to/manifest.json --db-path /tmp/execution.duckdb
```



---

<a id="artifacts--reproducibility"></a>
## Artifacts & Reproducibility

Artifacts are immutable and hash-addressed. Replaying a run verifies hashes before returning outputs.

```bash
bijux-llm-flows diff run <run_a> <run_b> --tenant-id <tenant> --db-path /tmp/execution.duckdb
```

Docs: [Execution Lifecycle](https://bijux.github.io/agentic-flows/architecture/execution_lifecycle/) · [Invariants](https://bijux.github.io/agentic-flows/architecture/invariants/)



---

<a id="api-surface"></a>
## API Surface

The HTTP API exposes the same contracts as the CLI.

Docs: [API Overview](https://bijux.github.io/agentic-flows/api/overview/) · [Schema](https://bijux.github.io/agentic-flows/api/schema/)



---

<a id="built-in-commands"></a>
## Built-in Commands

| Command | Description | Example |
| ------- | ----------- | ------- |
| `plan` | Resolve a manifest into a plan | `bijux-llm-flows plan manifest.json` |
| `run` | Execute a flow | `bijux-llm-flows run manifest.json --db-path /tmp/flow.duckdb` |
| `dry-run` | Trace execution without calling tools | `bijux-llm-flows dry-run manifest.json --db-path /tmp/flow.duckdb` |
| `inspect run` | Inspect a stored run | `bijux-llm-flows inspect run <run_id> --tenant-id <tenant> --db-path /tmp/flow.duckdb` |
| `diff run` | Compare two runs | `bijux-llm-flows diff run <a> <b> --tenant-id <tenant> --db-path /tmp/flow.duckdb` |

Full surface: [CLI Surface](https://bijux.github.io/agentic-flows/interface/cli_surface/)



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
../../apis/bijux-llm-flows/  # Root-managed OpenAPI schemas
../../configs/agentic-flows/  # Root-managed lint/type/security configs
docs/           # MkDocs site
../../makes/agentic-flows/  # Root-managed task modules (docs, test, lint, etc.)
../../scripts/bijux-llm-flows/  # Root-managed helper scripts
src/agentic_flows/  # Runtime + CLI implementation
tests/          # unit / regression / e2e
```



---

<a id="docs--resources"></a>
## Docs & Resources

* **Overview**: [Why agentic-flows exists](https://bijux.github.io/agentic-flows/overview/why-agentic-flows/) · [Mental model](https://bijux.github.io/agentic-flows/overview/mental-model/) · [Minimal run](https://bijux.github.io/agentic-flows/overview/minimal-run/) · [Relationship to agentic-proteins](https://bijux.github.io/agentic-flows/overview/relationship-to-agentic-proteins/) · [Audience](https://bijux.github.io/agentic-flows/overview/audience/)
* **Concepts**: [Concepts index](https://bijux.github.io/agentic-flows/concepts/) · [Determinism](https://bijux.github.io/agentic-flows/concepts/determinism/) · [Failures](https://bijux.github.io/agentic-flows/concepts/failures/)
* **Execution**: [Failure paths](https://bijux.github.io/agentic-flows/execution/failure-paths/)
* **Site**: https://bijux.github.io/agentic-flows/
* **Changelog**: https://github.com/bijux/bijux-llm-nexus/blob/main/packages/bijux-llm-flows/CHANGELOG.md
* **Repository**: https://github.com/bijux/bijux-llm-nexus/tree/main/packages/bijux-llm-flows
* **Issues**: https://github.com/bijux/bijux-llm-nexus/issues
* **Security** (private reports): https://github.com/bijux/bijux-llm-nexus/security/advisories/new
* **Artifacts**: https://bijux.github.io/agentic-flows/artifacts/



---

<a id="contributing"></a>
## Contributing

Welcome. See **[governance/contributing.md](governance/contributing.md)** for package workflow and contribution guidance.



---

<a id="license"></a>
## License

MIT — see **[LICENSE](https://github.com/bijux/bijux-llm-nexus/blob/main/LICENSE)**.
© 2025 Bijan Mousavi.
