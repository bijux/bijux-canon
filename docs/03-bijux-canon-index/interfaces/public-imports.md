---
title: Public Imports
audience: developers
type: reference
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-07-21
---

# Public Imports

The package root deliberately exports version metadata only:

```python
from bijux_canon_index import __version__
```

Import operational types from the namespace that owns their contract. This
keeps backend adapters and orchestration details from becoming accidental API.

## Supported Namespaces

| Need | Import surface |
| --- | --- |
| core corpus and execution models | `bijux_canon_index.core.model` |
| plans, sessions, modes, and execution identity | `bijux_canon_index.core.runtime` |
| validated HTTP request models | `bijux_canon_index.interfaces.schemas` |
| in-process execution facade | `bijux_canon_index.application.engine` |
| FastAPI application factory | `bijux_canon_index.api.v1` |

For example:

```python
from bijux_canon_index.application.engine import VectorExecutionEngine
from bijux_canon_index.core.model import ExecutionBudget, ExecutionRequest
from bijux_canon_index.core.runtime import ExecutionIntent, ExecutionMode
from bijux_canon_index.core.contracts import ExecutionContract

request = ExecutionRequest(
    request_id="retention-query",
    text=None,
    vector=(0.2, 0.8),
    top_k=5,
    execution_contract=ExecutionContract.DETERMINISTIC,
    execution_intent=ExecutionIntent.EXACT_VALIDATION,
    execution_mode=ExecutionMode.STRICT,
    execution_budget=ExecutionBudget(max_latency_ms=250),
)

engine = VectorExecutionEngine()
capabilities = engine.capabilities()
```

Capability discovery is safe before submitting the request; actual execution
also needs an artifact and configured backend state. The example intentionally
does not imply that constructing a request creates or populates a corpus.

## HTTP Models and Application

```python
from bijux_canon_index.api.v1 import build_app
from bijux_canon_index.interfaces.schemas import ExecutionRequestPayload
```

Boundary payloads are strict validation models. Core dataclasses express domain
invariants. Do not substitute one for the other merely because their field names
overlap.

Avoid imports from `infra.adapters`, `application.orchestration`, CLI command
modules, or underscore-prefixed modules. They are implementation surfaces and
may evolve without root-level compatibility guarantees. `bijux_vex` forwards
the canonical package for legacy consumers; new code should use the canonical
namespace.

See [Data Contracts](data-contracts.md) for the distinction between core and
boundary models.
