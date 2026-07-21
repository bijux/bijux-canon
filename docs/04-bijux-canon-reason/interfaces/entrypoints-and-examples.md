---
title: Entrypoints and Examples
audience: mixed
type: how-to
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-07-21
---

# Entrypoints and Examples

Use the package root for stable reasoning models and validation helpers, the
console command for durable runs, and the v1 API when another process owns the
request boundary.

## Python: define content-addressed work

`ProblemSpec` derives its identifier from canonical content. Equivalent input
produces the same identifier independently of object creation order.

```python
from bijux_canon_reason import ProblemSpec, canonical_dumps

spec = ProblemSpec(
    description="Determine the retention period supported by the evidence.",
    constraints={"require_citation": True},
    expected_output_type="Claim",
    expected={"subject": "signed run records"},
    version=1,
)

print(spec.id)
print(canonical_dumps(spec.model_dump(mode="json")))
```

The root also exports `Plan`, `PlanNode`, `Claim`, `EvidenceRef`, `SupportRef`,
`ToolRequest`, `ToolResult`, `Trace`, `VerificationReport`, fingerprint helpers,
and validators for plans, traces, and reports.

## CLI: create a verified run

Save a problem specification as `problem.json`:

```json
{
  "description": "Determine the retention period supported by the evidence.",
  "constraints": {"require_citation": true},
  "expected_output_type": "Claim",
  "expected": {"subject": "signed run records"},
  "version": 1
}
```

Then build the plan, execute it, verify the resulting trace, and write the run
bundle:

```bash
bijux-canon-reason run \
  --spec problem.json \
  --preset default \
  --seed 0 \
  --artifacts-dir artifacts/bijux-canon-reason \
  --fail-on-verify \
  --json
```

The command returns the run directory and verification summary. Each run
contains:

| Artifact | Meaning |
| --- | --- |
| `spec.json` | canonical problem declaration |
| `plan.json` | content-addressed plan and dependencies |
| `trace.jsonl` | ordered reasoning and tool events |
| `verify.json` | verification report produced with the run |
| `fingerprint.txt` | canonical trace fingerprint |
| `run_meta.json` | schema, producer, and runtime identity |
| `manifest.json` | bound inventory and invariant checksum |

## Verify and replay an existing run

```bash
RUN_DIR="artifacts/bijux-canon-reason/runs/<run-id>"

bijux-canon-reason verify \
  --trace "$RUN_DIR/trace.jsonl" \
  --plan "$RUN_DIR/plan.json" \
  --fail-on-verify \
  --json

bijux-canon-reason replay \
  --trace "$RUN_DIR/trace.jsonl" \
  --fail-on-diff \
  --json
```

Standalone verification writes `verify.verify.json` beside the trace. Replay
writes a replay trace and compares canonical fingerprints; it does not invoke
live tools in place of the recorded results.

## Serve the HTTP API

```bash
uvicorn bijux_canon_reason.api.v1.app:app --host 127.0.0.1 --port 8000
```

Create a run with the same problem contract:

```bash
curl --fail-with-body http://127.0.0.1:8000/v1/runs \
  --header 'content-type: application/json' \
  --data '{
    "spec": {
      "description": "Determine the retention period supported by the evidence.",
      "constraints": {"require_citation": true},
      "expected_output_type": "Claim",
      "version": 1
    },
    "preset": "default",
    "seed": 0
  }'
```

Use the returned `run_id` with:

- `GET /v1/runs/{run_id}` for metadata;
- `GET /v1/runs/{run_id}/manifest` for the bound artifact inventory;
- `GET /v1/runs/{run_id}/trace` for JSONL events;
- `POST /v1/runs/{run_id}/verify` for a fresh verification report;
- `POST /v1/runs/{run_id}/replay` for fingerprint comparison.

The checked-in [`v1 schema`](https://github.com/bijux/bijux-canon/blob/main/apis/bijux-canon-reason/v1/schema.yaml)
is authoritative for request limits, error envelopes, item CRUD, and run
lifecycle responses.
