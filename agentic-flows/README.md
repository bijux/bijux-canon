# Agentic Flows  
<a id="top"></a>

**A deterministic, contract-first execution and replay framework** — strict invariants, reproducible runs, and traceable outputs. Build audit-ready agent workflows with stable artifacts and replayable traces.  

Non-determinism is explicitly declared, budgeted, classified, governed, and audited.
Determinism is a policy decision, not a binary property.

v1 scope covers deterministic execution, replay, and contract verification for offline workflows; it is intended for research engineers and platform teams who need audit-grade runs, and it is not for interactive chat systems, autonomous agents, or low-latency production serving.

This system prioritizes replayability and auditability over convenience and speed.

[![PyPI - Version](https://img.shields.io/pypi/v/agentic-flows.svg)](https://pypi.org/project/agentic-flows/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://pypi.org/project/agentic-flows/)
[![Typing: typed (PEP 561)](https://img.shields.io/badge/typing-typed-4F8CC9.svg)](https://peps.python.org/pep-0561/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-green.svg)](https://github.com/bijux/agentic-flows/blob/main/LICENSE)
[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-brightgreen)](https://bijux.github.io/agentic-flows/)
[![CI Status](https://github.com/bijux/agentic-flows/actions/workflows/ci.yml/badge.svg)](https://github.com/bijux/agentic-flows/actions)

> **At a glance:** deterministic execution • invariant enforcement • replayable traces • CLI surface • structured telemetry  
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
pipx install agentic-flows  # Or: pip install agentic-flows
agentic-flows --help
agentic-flows run examples/boring/flow.json --policy examples/boring/policy.json --db-path /tmp/flows.duckdb
```



---

<a id="key-features"></a>
## Key Features

* **Deterministic execution** — reproducible runs with explicit budgets.
* **Contract-first design** — schema and invariants enforced at boundaries.
* **Replayable traces** — audit-grade execution records.
* **Structured telemetry** — correlation IDs and traceable events.



---

<a id="installation"></a>
## Installation

Requires **Python 3.11+**.

```bash
# Isolated install (recommended)
pipx install agentic-flows

# Standard
pip install agentic-flows
```

Upgrade: `pipx upgrade agentic-flows` or `pip install --upgrade agentic-flows`.



---

<a id="quick-start"></a>
## Quick Start

```bash
# Discover commands/flags
agentic-flows --help

# Run a deterministic execution
agentic-flows run examples/boring/flow.json --policy examples/boring/policy.json --db-path /tmp/flows.duckdb
```



---

<a id="artifacts--reproducibility"></a>
## Artifacts & Reproducibility

Artifacts are immutable and hash-addressed. Replaying a run verifies hashes before returning outputs.

```bash
agentic-flows replay examples/boring/flow.json --policy examples/boring/policy.json --run-id <run_id> --tenant-id <tenant> --db-path /tmp/flows.duckdb
```

Docs: [Execution Lifecycle](https://bijux.github.io/agentic-flows/architecture/execution_lifecycle/) · [Invariants](https://bijux.github.io/agentic-flows/architecture/invariants/)



---

<a id="api-surface"></a>
## API Surface

HTTP API is experimental and currently unimplemented.

Docs: [API Overview](https://bijux.github.io/agentic-flows/api/overview/) · [Schema](https://bijux.github.io/agentic-flows/api/schema/)



---

<a id="built-in-commands"></a>
## Built-in Commands

| Command | Description | Example |
| ------- | ----------- | ------- |
| `run` | Execute a flow | `agentic-flows run examples/boring/flow.json --policy examples/boring/policy.json --db-path /tmp/flow.duckdb` |
| `replay` | Replay a stored run | `agentic-flows replay examples/boring/flow.json --policy examples/boring/policy.json --run-id <run_id> --tenant-id <tenant> --db-path /tmp/flow.duckdb` |
| `inspect run` | Inspect a stored run | `agentic-flows inspect run <run_id> --tenant-id <tenant> --db-path /tmp/flow.duckdb` |

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
api/            # OpenAPI schemas
config/         # Lint/type/security configs
docs/           # MkDocs site
makefiles/      # Task modules (docs, test, lint, etc.)
scripts/        # Helper scripts
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
* **Changelog**: https://github.com/bijux/agentic-flows/blob/main/CHANGELOG.md
* **Repository**: https://github.com/bijux/agentic-flows
* **Issues**: https://github.com/bijux/agentic-flows/issues
* **Security** (private reports): https://github.com/bijux/agentic-flows/security/advisories/new
* **Artifacts**: https://bijux.github.io/agentic-flows/artifacts/



---

<a id="contributing"></a>
## Contributing

Welcome. See **[CONTRIBUTING.md](https://github.com/bijux/agentic-flows/blob/main/CONTRIBUTING.md)** for setup and test guidance.



---

<a id="license"></a>
## License

Apache-2.0 — see **[LICENSE](https://github.com/bijux/agentic-flows/blob/main/LICENSE)**.
© 2025 Bijan Mousavi.


---

This system is designed for auditability and replay, not exploratory or interactive use.

## Non-goals

- Automatic agent self-improvement or learning

## Publishing status

Current maturity: experimental research framework. v0.x carries no backward compatibility guarantees; schema compatibility is the only API guarantee. CLI output formatting and observability summaries may change without notice. Internal execution and verification APIs are not stable. Production usage should gate on strict determinism and explicit contracts.
