---
title: Public Imports
audience: developers
type: reference
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-07-21
---

# Public Imports

The package root is intentionally small. It lazily exposes only the HTTP API
version:

```python
from bijux_canon_agent import API_VERSION
```

Import application capabilities from the facade that owns them.

## Supported Facades

| Need | Import surface |
| --- | --- |
| validated agent calls and outputs | `bijux_canon_agent.contracts` |
| pipeline construction | `bijux_canon_agent.pipeline` |
| built-in roles | `bijux_canon_agent.agents` |
| trace validation and replay models | `bijux_canon_agent.traces` |
| ASGI application | `bijux_canon_agent.api.v1` |
| runtime-safe configuration | `bijux_canon_agent.config` |

```python
from bijux_canon_agent.contracts import AgentInput
from bijux_canon_agent.enums import AgentType, ExecutionMode

request = AgentInput(
    task_goal="Summarize the retention rule without unsupported claims.",
    payload={"text": "Retain signed records for seven years."},
    context_id="retention-policy-17",
    agent_type=AgentType.PLANNER,
    execution_mode=ExecutionMode.SYNC,
)
```

Construction validates the contract but does not execute a role or contact a
model provider.

## Pipeline, Trace, and API Imports

```python
from bijux_canon_agent.api.v1 import API_VERSION, create_app
from bijux_canon_agent.pipeline import AuditableDocPipeline, PipelineDefinition
from bijux_canon_agent.traces import RunTrace, validate_trace_payload
```

The pipeline facade is import-light and resolves its implementations lazily.
The trace facade includes v1 and v2 validators plus the explicit upgrader. The
API factory owns the deterministic offline HTTP boundary.

Avoid imports from `pipeline.execution`, `interfaces.cli`, individual
orchestration helpers, or underscore-prefixed modules. Those modules implement
the facades and may be reorganized without becoming package-root API.

`bijux_agent` forwards the canonical namespace for legacy consumers. New code
should use `bijux_canon_agent`; see
[Compatibility Commitments](compatibility-commitments.md) for the migration
boundary.
