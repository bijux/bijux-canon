---
title: Common Workflows
audience: mixed
type: how-to
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-08-25
---

# Common Workflows

Runtime v2 operations preserve evidence through one sequence: validate the
workspace and profile, submit durable work, resolve the terminal result,
inspect causal state, then replay, compare, cancel, or recover deliberately.

## Run the complete lexical workflow

```bash
bijux-canon-runtime init --workspace ./canon-workspace --json
export BIJUX_CANON_RUNTIME_WORKING_ROOT=./canon-workspace

bijux-canon-runtime v2 run \
  "What evidence does this corpus support?" \
  --source-directory ./documents \
  --profile offline-lexical \
  --wait \
  --wait-timeout-seconds 30
```

The operation discovers regular admitted documents, retains their original
bytes, prepares an immutable corpus, builds the selected index, retrieves
bounded evidence, produces a citation-required answer, and records bounded
research and agent evidence. Each transition is retained under one job, run,
attempt, configuration and causal artifact graph.

## Control each lifecycle explicitly

Use separate commands when corpus and index reuse matters:

```bash
bijux-canon-runtime v2 ingest ./documents \
  --profile offline-lexical \
  --wait
bijux-canon-runtime v2 index CORPUS_ID \
  --profile offline-lexical \
  --wait
bijux-canon-runtime v2 search "bounded query" \
  --index-id INDEX_ID \
  --profile offline-lexical \
  --wait
bijux-canon-runtime v2 ask "grounded question" \
  --corpus-id CORPUS_ID \
  --index-id INDEX_ID \
  --profile offline-lexical \
  --wait
```

Use `v2 research` for counterevidence-aware bounded research. Every submission
accepts a strict `--request FILE` alternative for automation.

## Follow or cancel durable work

```bash
bijux-canon-runtime v2 status JOB_ID \
  --follow \
  --timeout-seconds 30
bijux-canon-runtime v2 cancel JOB_ID
```

Follow mode uses worker notification and a deadline. Client timeout and durable
cancellation are distinct states; inspect the job after either event.

## Inspect retained evidence

```bash
bijux-canon-runtime v2 result JOB_ID
bijux-canon-runtime v2 inspect RUN_ID \
  --attempt-id ATTEMPT_ID \
  --limit 20
bijux-canon-runtime v2 artifact-payload ARTIFACT_ID \
  --offset 0 \
  --max-bytes 65536
```

Inspection is bounded by default and summarizes oversized arbitrary values.
The payload command returns an independently verifiable digest, total size and
continuation offset for one immutable byte page.

## Replay and compare

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

Replay produces a new attempt and refuses changed or missing governed inputs.
Comparison retains both attempt identities and the selected comparison
dimensions; it never chooses tolerance after observing a favorable result.

## Back up or relocate

```bash
bijux-canon-runtime v2 backup nightly-2026-08-25
bijux-canon-runtime v2 restore BACKUP_GENERATION ./restored-workspace
```

Backup requires a quiescent workspace. Restore verifies the database, admitted
CAS, indexes, controls and workspace-owned model state before activating a new
destination. Use restore for relocation rather than moving a workspace tree.
