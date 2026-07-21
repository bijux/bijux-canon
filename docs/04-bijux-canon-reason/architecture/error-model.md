---
title: Error Model
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-07-22
---

# Error Model

`bijux-canon-reason` distinguishes an invalid request, an execution failure, a
verification finding, and a replay difference. Those outcomes mean different
things: only the first two prevent a run from being constructed, while the
latter two describe evidence about a completed artifact set.

```mermaid
flowchart LR
    A[Problem specification] --> B{Schema valid?}
    B -- no --> C[Validation error]
    B -- yes --> D{Plan is a DAG?}
    D -- no --> E[Topology error]
    D -- yes --> F[Execute tools]
    F -- failed --> G[Execution error]
    F -- completed --> H[Verification report]
    H --> I{Policy gate enabled?}
    I -- findings --> J[Exit 2]
    I -- clear or gate off --> K[Exit 0]
    K --> L[Optional replay comparison]
```

## Failure classes

| Class | Meaning | Representation |
| --- | --- | --- |
| Input validation | A `ProblemSpec`, API body, or serialized artifact violates its schema | Pydantic validation error; HTTP `422` at the API boundary |
| Plan topology | An edge names an unknown node, a dependency is missing, or the graph contains a cycle | exception containing invariant code `INV-ORD-001` |
| Tool execution | A planned tool invocation cannot produce its declared result | failed tool result; raised `RuntimeError` under the default fail-fast policy |
| Artifact integrity | Required evidence is absent or its SHA-256 digest differs | `FileNotFoundError` or `ValueError` while assembling or verifying artifacts |
| Verification | A completed trace violates a structural, provenance, grounding, or finalization invariant | typed entries in `VerificationReport.failures` |
| Replay | A rerun does not reproduce the recorded trace and outputs | structured replay diff; optionally a non-zero CLI exit |

Topology is checked before any node executes. This prevents partial traces from
being mistaken for complete runs. The executor's default policy is fail-fast;
callers using the Python API may opt out and inspect accumulated tool failures.

## Failure Ownership by Boundary

The boundary that can state the violated contract owns the primary error. Later
layers may add context, but they must preserve the original classification.

| Boundary | Owns | Must preserve |
| --- | --- | --- |
| request adapter | malformed or schema-invalid input | field path and validation detail |
| planner | invalid dependencies or cyclic topology | invariant identifier and offending nodes |
| runtime adapter | tool invocation or declared-output failure | tool identity, request linkage, and failed result |
| artifact writer | missing files or digest mismatch | expected path or digest and observed value |
| verifier | structural, grounding, provenance, or finalization finding | check ID, severity, and referenced evidence |
| replay comparator | difference between original and replay artifacts | compared identities and structural difference |

```mermaid
stateDiagram-v2
    [*] --> Requested
    Requested --> Rejected: schema invalid
    Requested --> Planned: topology valid
    Planned --> ExecutionFailed: tool or runtime failure
    Planned --> Executed: actions complete
    Executed --> VerifiedWithFindings: report contains findings
    Executed --> VerifiedClear: report has no retained findings
    VerifiedWithFindings --> Published: policy gate disabled
    VerifiedWithFindings --> Gated: policy gate enabled
    VerifiedClear --> Published
    Published --> ReplayDifferent: structural diff found
    Published --> ReplayEquivalent: comparison passes
    Rejected --> [*]
    ExecutionFailed --> [*]
    Gated --> [*]
    ReplayDifferent --> [*]
    ReplayEquivalent --> [*]
```

`Published` in this model means the artifact set was written; it does not mean
that verification was clear. The retained report is authoritative about that
difference. Similarly, `ReplayDifferent` is a completed comparison, not a
transport exception.

## Findings are data

A verification failure is not an exception. `verify_trace` returns a report
with its own content-derived identifier, the checks performed, typed failures,
and summary metrics. Findings have `info`, `warning`, or `error` severity and
are filtered according to the selected policy:

- `strict` retains every finding;
- `audit` also retains every finding for inspection;
- `permissive` retains only error-severity findings.

The CLI makes the policy decision explicit. `run --fail-on-verify` exits with
status `2` when the generated verification report contains failures. Without
that flag, the command still writes `verify.json` and reports the failure count.
Likewise, replay differences become exit status `2` only when
`--fail-on-diff` is enabled.

## What a caller can rely on

Every successful artifact-producing run writes the specification, plan, JSONL
trace, verification report, fingerprint, run metadata, and manifest beneath one
run directory. A consumer should treat the manifest and digests as the
integrity boundary and the verification report as the semantic assessment.
Neither an exit status of zero nor a digest match alone establishes that a
claim is scientifically true.

For automation, inspect the structured report or replay result before applying
the CLI policy gate. Exit status `2` communicates that an enabled gate rejected
the findings; it intentionally does not collapse their invariant IDs,
severities, or evidence references into a single boolean.
