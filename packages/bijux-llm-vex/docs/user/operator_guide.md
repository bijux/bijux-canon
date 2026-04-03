# Operator Guide

This guide covers production operations for Bijux Vex.

## Running FastAPI

- Use a process manager (systemd, container runtime) with `uvicorn`.
- Example: `uvicorn bijux_vex.boundaries.api.app:app --host 0.0.0.0 --port 8000`
- Configure workers based on CPU cores and expected concurrency.

## Config + Env Patterns

- Prefer explicit config files created via `bijux vex init`.
- Use `BIJUX_VEX_STATE_PATH` and `BIJUX_VEX_RUN_DIR` to isolate storage per service.
- Avoid implicit vector store selection; set `vector_store.backend` explicitly.

## Safe Logging

- Use `BIJUX_VEX_LOG_FORMAT=json` for structured logs.
- Never log raw URIs with credentials; redaction is enforced on vector store URIs.

## Scaling Guidance

- Increase workers for request concurrency.
- Keep vector store backend local for low latency; use Qdrant for remote scaling.
- Use `resource_limits` to prevent abusive requests.
