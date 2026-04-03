# Architecture contract

This page captures the maintainer rules for changing package layout and runtime behavior without creating silent drift.

## What must remain stable

- `docs/spec/*` stays authoritative for public guarantees unless you intentionally version a breaking change.
- Trace schema changes remain explicit, versioned, and replay-safe.
- The canonical pipeline lifecycle and allowed transitions do not change without spec and test updates.
- Final artifacts stay trace-backed; no execution path may bypass trace recording.
- Documentation, tests, and package metadata must describe the current tree and identity.

## What belongs in this package

- pipeline orchestration and lifecycle control
- agent runtime behavior and audit traces
- CLI and HTTP entrypoints for running and replaying the pipeline
- reference configuration and reference pipeline builders for adoption

## What does not belong here

- product-specific workflows that should live in an app layer
- hidden state across runs
- silent retries or fallback behavior outside declared policy
- checked-in runtime artifacts under `src/`

## Change checklist

1. Update code, tests, and docs in the same change.
2. Re-run the package test slices that exercise the touched boundary.
3. If public behavior moved, update `docs/project_overview.md`, maintainer docs, and package metadata.
4. If contracts changed, update the spec first and treat it as a versioned change.
