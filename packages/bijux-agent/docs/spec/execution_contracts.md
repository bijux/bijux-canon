# Execution contracts (spec)

## Input contract (context)

A pipeline run consumes a mapping called the **context**.

Required keys:

- `task_goal` (string)

Optional keys:

- `context_id` (string)
- `text` (string) — inline input
- `file_path` (string) — path to a file containing the input

Constraints:

- At least one of `text` or `file_path` MUST be provided.
- Additional keys MAY be present to support domain-specific workflows.

### CLI mapping

The CLI constructs context from:

- `task_goal` from YAML config (`task_goal`, or a built-in default)
- `file_path` from the input path (file) or each file in the input directory
- `context_id` derived from the file stem

### API v1 mapping

The API v1 handler constructs context from:

- `text` and `task_goal` in the request
- `context_id` (default `api-v1`)
- a deterministic on-disk snapshot path written under `./artifacts/api/inputs/`

## Output contract

The pipeline returns a mapping with (at minimum):

- `stages`: `{stage_name: stage_output}`
- `final_status`: a summary object

`final_status` MUST include:

- `success` (bool)
- `termination_reason`
- `stages_processed` (list of strings)
- `iterations` (int)

## Dry-run semantics

- Dry-run MUST NOT claim model-derived outputs.
- Dry-run MUST still produce a coherent `final_result.json` suitable for wiring checks.
