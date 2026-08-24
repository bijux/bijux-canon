---
title: HTTP API
audience: mixed
type: reference
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-08-25
---

# HTTP API

The `api` installation profile supplies an installed loopback-first server for
the Runtime v2 application service:

```bash
python -m pip install 'bijux-canon-runtime[api]'
bijux-canon-runtime init --workspace ./canon-workspace --json
bijux-canon-runtime-server --workspace ./canon-workspace
```

The default bind is `127.0.0.1:8000`. Use `--host`, `--port`, `--log-level`,
and `--no-access-log` deliberately when the surrounding deployment supplies
its own authentication, authorization, isolation, and request limits. The
Runtime server does not provide those controls.

Every v2 request must send `Bijux-API-Version: v2`. Durable workflow submissions
also require an `Idempotency-Key` of 16 to 200 characters. The response header
`Bijux-API-Supported-Versions: v2` identifies the supported contract.

## Probe The Installed Service

```bash
curl --fail-with-body \
  -H 'Bijux-API-Version: v2' \
  http://127.0.0.1:8000/api/v2/live

curl --fail-with-body \
  -H 'Bijux-API-Version: v2' \
  'http://127.0.0.1:8000/api/v2/ready?operation=initialized'

curl --fail-with-body \
  -H 'Bijux-API-Version: v2' \
  http://127.0.0.1:8000/api/v2/capabilities
```

Liveness proves that the process can answer. Readiness evaluates the requested
capability and optional execution profile against the effective workspace.
Capability discovery reports configuration identities, installed support,
requirements, and remediation without returning credential values.

## Implemented V2 Surface

The service composes the same application layer as the Python and CLI adapters:

| Operation | HTTP route |
| --- | --- |
| prepare and inspect a corpus | `POST /api/v2/corpora/prepare`, `GET /api/v2/corpora/{corpus_id}` |
| build and inspect an index | `POST /api/v2/indexes/build`, `GET /api/v2/indexes/{index_id}` |
| retrieve evidence | `POST /api/v2/retrievals` |
| answer and research | `POST /api/v2/answers`, `POST /api/v2/research` |
| run the linked workflow | `POST /api/v2/runs` |
| inspect and replay a run | `GET /api/v2/runs/{run_id}`, `POST /api/v2/runs/{run_id}/replays` |
| inspect, wait for, resolve, or cancel a job | `/api/v2/jobs/{job_id}` and child routes |
| compare attempts | `POST /api/v2/comparisons` |
| page immutable payload bytes | `GET /api/v2/artifacts/{artifact_id}/payload` |
| evaluate reviewed retrieval cases | `POST /api/v2/retrieval-evaluations` |

Submissions return bounded durable job-status documents. Resolve completed
results through the job result route. Inspection, comparison, index segments,
and artifact payload bytes use explicit limits and opaque continuation cursors.
Backup and restore remain local CLI operations because they require direct
filesystem authority over a quiescent workspace.

The pinned OpenAPI document and migration policy are under
[`apis/bijux-canon-runtime/v2/`](https://github.com/bijux/bijux-canon/tree/main/apis/bijux-canon-runtime/v2).
Route behavior, generated OpenAPI, its pin, and the schema hash must agree.

## Errors And Correlation

Failures use `application/problem+json` and the shared Runtime problem fields:
code, title, status, retryability, remediation, bounded cause, correlation ID,
and optional run ID. Supply `X-Correlation-ID`, or a request context correlation
identity where the schema supports one. Unsupported versions return `406` and
the supported-version response header. Validation, not-found, conflict,
capability, and operation failures retain distinct typed codes.

## V1 Compatibility Status

The installed server command serves v2 only. It does not mount the older v1
application. `bijux_canon_runtime.api.v1.app:app` remains importable for callers
that explicitly host that compatibility module. Its health and readiness probes
are implemented, while `POST /api/v1/flows/run` and
`POST /api/v1/flows/replay` validate their legacy envelopes and then return
`501 Not Implemented`. A v1 schema or import is not evidence of an executable
v1 workflow.
