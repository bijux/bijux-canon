# Agent output expectations (spec)

This document describes what downstream code is allowed to assume about agent outputs.

## Required fields

An agent output MUST include:

- `text`: non-empty string
- `confidence`: float in `[0, 1]`
- `metadata.contract_version`: must equal the runtime `CONTRACT_VERSION`

## Optional fields

An agent output MAY include:

- `artifacts`: structured payloads for consumers
- `scores`: named numeric judgments
- additional metadata (provenance, citations, etc.)

## Why this is strict

Without a stable output contract:

- the decision layer becomes brittle,
- traces become hard to validate,
- replay tooling cannot safely reason about the run.

If you need a new output shape, extend `artifacts` rather than weakening the schema.
