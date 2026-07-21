---
title: Entrypoints and Examples
audience: mixed
type: how-to
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-07-21
---

# Entrypoints and Examples

Use package-owned contract modules for in-process composition, the console
command for document files, and the v1 ASGI application for deterministic
offline HTTP execution.

## Python: create a strict agent input

The package root intentionally exposes only `API_VERSION`. Import contracts
from their owning modules:

```python
from bijux_canon_agent.contracts.runtime_models import AgentInput
from bijux_canon_agent.enums import AgentType, ExecutionMode

request = AgentInput(
    task_goal="Summarize the retention obligation with no unsupported claims.",
    payload={"text": "Keep signed run records for seven years."},
    context_id="retention-policy-17",
    agent_type=AgentType.PLANNER,
    execution_mode=ExecutionMode.SYNC,
)

print(request.model_dump(mode="json"))
```

Unknown fields, blank identifiers, and mutation after construction are
rejected. Constructing a contract object does not execute a provider call; use
the pipeline or an interface boundary for orchestration.

## CLI: process a document or directory

```bash
bijux-canon-agent run documents/ \
  --config packages/bijux-canon-agent/examples/reference-config.yml \
  --out artifacts/bijux-canon-agent
```

For one successful input, the command prints the structured result. The output
directory contains `result/final_result.json` and, for a non-dry run,
`trace/run_trace.json`. The final result records verdict, confidence,
epistemic status, termination and convergence state, model metadata, runtime
version, and the trace path.

Inspect file resolution and artifact behavior without executing the pipeline:

```bash
bijux-canon-agent run report.txt \
  --config packages/bijux-canon-agent/examples/reference-config.yml \
  --out artifacts/bijux-canon-agent \
  --dry-run
```

### Current credential constraint

The CLI validates `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`,
`HUGGINGFACE_API_KEY`, and `DEEPSEEK_API_KEY` before argument parsing. As a
result, `--help`, `--version`, dry-run, and replay require all four variables
to be present even when the selected workflow does not contact those
providers. Supply them through the process environment or an approved secret
manager; never place credentials in the YAML file or committed shell scripts.

## CLI: reconstruct a recorded outcome

```bash
bijux-canon-agent replay artifacts/bijux-canon-agent/trace/run_trace.json
```

Replay upgrades the trace, validates schema compatibility and minimal shape,
reconstructs the pipeline verdict, confidence, epistemic status, and stop
reason, then compares those four fields with `result/final_result.json` when
that file is adjacent to the trace directory. It reports when the final result
is absent instead of claiming parity. This is stored-outcome reconstruction,
not role or provider re-execution; a mismatch is printed but does not currently
produce a nonzero exit status.

## HTTP: run the offline v1 pipeline

The API application is an ASGI factory:

```bash
uvicorn bijux_canon_agent.api.v1.app:create_app \
  --factory --host 127.0.0.1 --port 8000
```

Both version-prefixed and normalized routes are accepted. Use the public v1
form:

```bash
curl --fail-with-body http://127.0.0.1:8000/v1/run \
  --header 'content-type: application/json' \
  --data '{
    "text": "Keep signed run records for seven years.",
    "task_goal": "Summarize the retention obligation.",
    "context_id": "retention-policy-17",
    "config": {
      "agents": ["file_reader", "summarizer", "validator", "critique"],
      "strategy": "extractive",
      "backend": "simple"
    }
  }'
```

The HTTP handler uses a fixed deterministic, offline configuration. The v1
schema accepts `extractive` strategy and `simple` backend; provider and model
selection are not client-controlled through this boundary. Responses carry a
context identifier and either a structured result or a structured error.

Use `GET /v1/health` for process health. The authoritative payload and error
contract is the checked-in
[`v1 schema`](https://github.com/bijux/bijux-canon/blob/main/apis/bijux-canon-agent/v1/schema.yaml).
