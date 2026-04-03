# Example: document review workflow

This example shows how to use Bijux Agent as an auditable “review runner” over a directory of documents.

## Goal

Given a folder of files, produce per-file structured results and an overall run verdict you can audit.

## Recommended setup

1. Put your documents in a single directory (non-recursive processing today).
2. Set a review-oriented task goal in your config, for example:

```yaml
task_goal: "review this document for correctness, missing assumptions, and actionable revisions"
```

## Run

```bash
python -m bijux_agent.main run path/to/review_corpus --out artifacts/review_run --config config/config.yml
```

## How to interpret the outputs

- `artifacts/review_run/result/final_result.json` is the first file to read.
- `artifacts/review_run/trace/run_trace.json` is what you use to validate:
  - which model metadata was used,
  - what the replayability classification is,
  - what fingerprints identify the run inputs and config.

## Practical advice

- Keep the task goal narrow. “Review everything” yields unstable scope and weak auditability.
- Treat the run directory as immutable once produced; regeneration should go to a new `--out` directory.

See also:

- `docs/user/usage.md` (CLI mechanics)
- `docs/spec/failure_model.md` (how failures are represented)
