---
title: Public Imports
audience: developers
type: reference
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-07-21
---

# Public Imports

The package root exposes the stable reasoning model and its identity and
validation helpers. Prefer it for constructing or reading specs, plans, traces,
claims, evidence, and verification reports.

## Root Surface

| Concern | Root imports |
| --- | --- |
| problem and plan | `ProblemSpec`, `Plan`, `PlanNode`, `StepSpec`, `ToolRequest` |
| runtime identity | `RuntimeDescriptor`, `ToolDescriptor` |
| tool execution | `ToolCall`, `ToolResult` |
| trace | `Trace`, `TraceEvent`, `TraceEventKind`, `StepOutput` |
| evidence and claims | `EvidenceRef`, `SupportRef`, `SupportKind`, `Claim` |
| verification | `VerificationCheck`, `VerificationReport` |
| identity | `canonical_dumps`, `fingerprint_bytes`, `fingerprint_obj`, `stable_id` |
| invariants | `validate_plan`, `validate_trace`, `validate_verification_report` |

## Construct Content-Addressed Records

```python
from bijux_canon_reason import Plan, PlanNode, ProblemSpec, StepSpec, validate_plan

spec = ProblemSpec(description="Which retained evidence supports the claim?")
node = PlanNode(
    kind="gather",
    step=StepSpec(kind="gather"),
)
plan = Plan(
    spec_id=spec.id,
    problem=spec.description,
    nodes=[node],
).with_content_id()

errors = validate_plan(plan)
if errors:
    raise ValueError(errors)
```

IDs are derived from canonical content. Build the complete record first; a
content change intentionally produces a different identity.

## Boundary Imports

Use explicit public namespaces when opting into an interface rather than a core
record:

```python
from bijux_canon_reason.api.v1 import create_app
from bijux_canon_reason.interfaces.serialization import (
    read_trace_jsonl,
    write_trace_jsonl,
)
```

The serialization namespace owns stable JSON and trace-file boundaries. The API
namespace owns the FastAPI application. Execution internals, individual check
modules, and CLI implementation modules should not be imported as library APIs.

`bijux_rar` forwards the canonical root and submodules for compatibility. New
code should import `bijux_canon_reason`; see
[Compatibility Commitments](compatibility-commitments.md) for migration rules.
