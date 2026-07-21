---
title: Public Imports
audience: developers
type: reference
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-07-21
---

# Public Imports

The root package is the primary execution facade:

```python
from bijux_canon_runtime import FlowManifest, RunMode, execute_flow
```

`RunMode` and `execute_flow` are resolved lazily, keeping manifest-only imports
lightweight. Calling `execute_flow(manifest)` without a configuration selects
live strict execution; use an explicit `ExecutionConfig` when planning,
observing, resuming, or binding governed stores and policies.

## Public Facades

| Need | Import surface |
| --- | --- |
| execution entrypoint | `bijux_canon_runtime` or `bijux_canon_runtime.runtime` |
| planning and flow boundary | `bijux_canon_runtime.application` |
| stable plan, trace, and replay models | `bijux_canon_runtime.model` |
| identifiers and semantic enums | `bijux_canon_runtime.ontology` |
| verification orchestration | `bijux_canon_runtime.verification` |
| versioned HTTP schemas and ASGI app | `bijux_canon_runtime.api.v1` |

```python
from bijux_canon_runtime import RunMode, execute_flow
from bijux_canon_runtime.application.execute_flow import ExecutionConfig
from bijux_canon_runtime.model import FlowManifest
from bijux_canon_runtime.ontology import DeterminismLevel
```

`FlowManifest` construction validates its dataclass shape. Execute through the
application boundary so contract validation, planning, determinism enforcement,
trace finalization, and persistence remain in the governed lifecycle.

## Model and API Boundaries

The stable model facade exports `FlowManifest`, `ExecutionPlan`,
`ExecutionTrace`, and `ReplayEnvelope`. The ontology facade owns typed IDs and
enums used across those models. The API facade exports `FlowRunRequest`,
`FlowRunResponse`, `ReplayRequest`, `FailureEnvelope`, and the ASGI app.

Avoid importing lifecycle preparation helpers, concrete executors, DuckDB
schema internals, or modules marked as internal. They implement the public
facades and can change as long as the governed contracts remain intact.

`bijux_canon` and `agentic_flows` forward the canonical package for compatibility.
New integrations should use `bijux_canon_runtime`; see
[Compatibility Commitments](compatibility-commitments.md) for correspondence
and migration rules.
