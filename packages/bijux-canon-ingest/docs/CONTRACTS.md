# Contracts

The stable surface of `bijux-canon-ingest` includes both its entrypoints and
the shapes callers depend on.

## Stable surfaces

- console entrypoint `bijux-canon-ingest`
- HTTP surface under `interfaces/http/`
- pinned API schema under `apis/bijux-canon-ingest/v1/schema.yaml`
- package-facing request, result, and configuration models

## Change policy

Internal modules may move between `application/`, `processing/`, `retrieval/`,
and `infra/`, but boundary behavior and package-facing shapes should change only
with documentation and test updates in the same review.
