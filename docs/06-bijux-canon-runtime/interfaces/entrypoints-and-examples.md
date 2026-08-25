---
title: Entrypoints and Examples
audience: mixed
type: how-to
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-08-25
---

# Entrypoints and Examples

Use the installed v2 CLI for local operation, the shared application service
for in-process composition, and the installed v2 server for HTTP integration.
All three adapters use the same workspace authority and typed operations.

## CLI: complete offline lexical run

The base Runtime wheel needs no model, optional extra, provider credential, or
network access for the lexical profile:

```bash
bijux-canon-runtime init --workspace ./canon-workspace --json
export BIJUX_CANON_RUNTIME_WORKING_ROOT=./canon-workspace

bijux-canon-runtime v2 ready \
  --operation run \
  --profile offline-lexical

bijux-canon-runtime v2 run \
  "What evidence does this corpus support?" \
  --source-directory ./documents \
  --profile offline-lexical \
  --wait \
  --wait-timeout-seconds 30
```

The terminal response is a bounded job document. Preserve its `job_id`,
`run_id`, and `attempt_id`; retrieve and inspect the larger records explicitly:

```bash
bijux-canon-runtime v2 result JOB_ID
bijux-canon-runtime v2 inspect RUN_ID \
  --attempt-id ATTEMPT_ID \
  --limit 20
```

Inspection reports counts and bounded collection pages. Large immutable
payloads are never dumped implicitly; use `v2 artifact-payload` with an offset
and byte limit when the payload itself is required.

## CLI: replay and compare

```bash
bijux-canon-runtime v2 replay RUN_ID \
  --source-attempt-id ATTEMPT_ID \
  --network-policy disabled \
  --wait

bijux-canon-runtime v2 compare RUN_ID RUN_ID \
  --baseline-attempt-id ATTEMPT_ID \
  --candidate-attempt-id REPLAY_ATTEMPT_ID \
  --dimension outcome \
  --dimension claims \
  --dimension citations
```

Replay creates a new attempt bound to the retained request, inputs,
configuration, artifacts and network policy. Comparison evaluates only the
requested dimensions and reports a typed disposition; it does not silently
promote similar prose into equivalent evidence.

## CLI: backup and restore

Quiesce the workspace before backup. Runtime refuses queued or running work,
missing admitted payloads, symlinks, external model state, and files that drift
during capture:

```bash
bijux-canon-runtime v2 backup nightly-2026-08-25
bijux-canon-runtime v2 restore BACKUP_GENERATION ./restored-workspace
```

Restore verifies the complete inventory before activating a destination that
must not already exist. It preserves the logical workspace identity while
rewriting governed machine-local paths. Directly copying or moving a workspace
is not a supported relocation operation.

## CPU-local dense and hybrid profiles

Install the local CPU extra, acquire the pinned model once, then validate it
offline before initializing a model-bound workspace:

```bash
python -m pip install 'bijux-canon-runtime[local-cpu]'

bijux-canon-index model acquire \
  --profile local-minilm-384 \
  --cache-root ./models

bijux-canon-index model validate \
  --model-root ./models/local-minilm-384/LOCKED_REVISION

bijux-canon-runtime init \
  --workspace ./hybrid-workspace \
  --model ./models/local-minilm-384/LOCKED_REVISION \
  --json
```

Acquisition is the only step that requires network access. Readiness rejects a
missing, corrupt, wrong-dimensional, incompatible, or unvalidated model before
durable work is queued.

## HTTP: installed v2 server

```bash
python -m pip install 'bijux-canon-runtime[api]'
bijux-canon-runtime init --workspace ./canon-workspace --json
bijux-canon-runtime-server --workspace ./canon-workspace

curl --fail-with-body -H 'Bijux-API-Version: v2' \
  http://127.0.0.1:8000/api/v2/live
curl --fail-with-body -H 'Bijux-API-Version: v2' \
  'http://127.0.0.1:8000/api/v2/ready?operation=initialized'
```

The server defaults to loopback and serves only Runtime v2. Durable submission
requests require an `Idempotency-Key`; result and inspection payloads require
deliberate follow-up. The host remains responsible for authentication,
authorization, TLS, tenant isolation, sandboxing and external request limits.

The separate v1 compatibility module remains importable but is not mounted by
the installed server. New integrations use the checked-in
[`v2 schema`](https://github.com/bijux/bijux-canon/blob/main/apis/bijux-canon-runtime/v2/schema.yaml).
