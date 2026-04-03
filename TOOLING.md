# Tooling

This repository separates package code from repository-owned tooling.

## Tooling Ownership

- `configs/<package>/` contains package-specific tool configuration
- `configs/shared/` contains shared baselines
- `makes/<package>/` contains package automation targets
- `makes/shared/` contains shared automation fragments

## Design Rule

If a tool setting exists only to support local package runtime behavior, keep
it with the package. If it defines repository policy or a shared workflow, keep
it in `configs/` or `makes/`.

## Current Tool Families

- packaging and build metadata
- test and coverage configuration
- linting and type-checking
- docs generation
- security and dependency auditing
