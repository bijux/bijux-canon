---
title: Configuration Surface
audience: mixed
type: reference
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-07-21
---

# Configuration Surface

The CLI reads a YAML document, then builds the auditable document pipeline.
Constructor arguments have highest precedence, followed by
`pipeline.parameters`, top-level values, and built-in defaults.

## Pipeline controls

| Setting | Default | Effect |
| --- | ---: | --- |
| `max_retries` | `2` | retry limit for retryable pipeline work |
| `chunk_size` | `1000` | document chunk target |
| `shard_threshold` | `1000000` | size at which work is sharded |
| `max_iterations` | `3` | convergence loop ceiling |
| `concurrency_limit` | `10` | maximum concurrent shard work |
| `stage_timeout` | `300.0` | per-stage timeout in seconds |
| `retry_delay` | `1.0` | delay between retries in seconds |
| `quality_threshold` | `0.8` | minimum score accepted at finalization |

`pipeline.policy.retry_allowed: false` is compatible only with
`max_retries: 0`; contradictory configuration is rejected. Feedback rules can
set `critique.retry_threshold` and `summarization.retry_on_empty`.

```yaml
task_goal: summarize this document

pipeline:
  parameters:
    max_retries: 2
    chunk_size: 1000
    shard_threshold: 1000000
    max_iterations: 3
    concurrency_limit: 10
    stage_timeout: 300.0
    retry_delay: 1.0
    quality_threshold: 0.8
  policy:
    retry_allowed: true
  feedback_rules:
    critique:
      retry_threshold: 0.5
    summarization:
      retry_on_empty: true

logging:
  log_dir: artifacts/05-bijux-canon-agent/logs
  log_level: INFO
  log_file_name: application.log
  structured_logging: true
  async_logging: true
  telemetry_enabled: true

model_metadata:
  provider: local
  model_name: auditable-doc-pipeline
  temperature: 0.0
  max_tokens: 512
```

`model_metadata` is required when the CLI writes the final trace. A trace may
be marked replayable only when temperature is exactly `0.0` and replay-critical
hashes and identifiers are present.

## CLI controls

`bijux-canon-agent run` requires an input file or directory and `--out` for the
result directory. `--config` defaults to `examples/reference-config.yml`.
`--dry-run` emits the planned trace without invoking the document pipeline, and
`--replay TRACE` attaches an existing trace to the run context. The dedicated
`replay TRACE` command compares a recorded trace with `final_result.json` when
that file is available.

The CLI loads `.env` from the working directory and currently validates all
four provider variables before it parses the command:

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `HUGGINGFACE_API_KEY`
- `DEEPSEEK_API_KEY`

This requirement also applies to help, version, dry-run, and replay invocations.
It is a CLI bootstrap constraint, not evidence that every run contacts every
provider.

## HTTP controls

The `POST /run` request accepts `text` (1–200,000 characters), `task_goal`
(1–4,000 characters), and `context_id` (1–128 characters). Although the schema
accepts a `config` object, the handler deliberately runs the fixed offline
`simple` backend with the `extractive` strategy and canonical agent list. Client
overrides do not alter execution in API v1.
