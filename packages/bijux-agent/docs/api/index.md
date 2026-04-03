# API (v1)

Bijux Agent provides a small HTTP surface meant for embedding the canonical pipeline in other systems.

## Mounting into FastAPI

`bijux_agent.httpapi.v1.build_router()` returns an `APIRouter` when FastAPI is installed.

```python
from fastapi import FastAPI
from bijux_agent.httpapi.v1 import build_router

app = FastAPI()
router = build_router()
if router:
    app.include_router(router)
```

## Endpoint: `POST /v1/run`

Request (`RunRequestV1`):

```json
{
  "text": "string (required)",
  "task_goal": "string (required)",
  "context_id": "api-v1",
  "config": { "optional": "shallow config overrides" }
}
```

Response (`RunResponseV1`):

```json
{
  "success": true,
  "context_id": "api-v1",
  "result": { "pipeline_result": "..." }
}
```

On failure:

```json
{
  "success": false,
  "context_id": "api-v1",
  "error": { "code": "EXECUTION_FAILED", "message": "…", "http_status": 422 },
  "result": { "pipeline_result": "may be present" }
}
```

## Artifact behavior

The v1 handler snapshots request text into:

- `./artifacts/api/inputs/`

and writes logs/results under:

- `./artifacts/api/`

This is deliberate: API runs must still be auditable.

## Error semantics

- Schema validation is performed by Pydantic. In FastAPI, invalid requests typically return HTTP 422.
- Execution failures map to `EXECUTION_FAILED`.
- Convergence failures map to `CONVERGENCE_FAILED`.
- Unexpected exceptions map to `INTERNAL_ERROR`.

## OpenAPI schema

The repository includes an OpenAPI file at `api/v1/schema.yaml`. Keep the router implementation and schema aligned (avoid “spec drift”).
