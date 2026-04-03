# Repository Tooling

The repository separates package code from repository-owned tooling.

## Configuration

- `configs/<package>/` contains repo-owned config for package tools
- `configs/shared/` contains shared baselines used across packages

Today this includes repository-owned configuration for:

- Ruff
- MkDocs
- pytest
- deptry
- coverage and type checking

## Automation

- `makes/<package>/` contains package task modules
- `makes/shared/` contains shared make fragments
- `Makefile` at the repository root orchestrates package targets
- `tox.ini` at the repository root orchestrates package validation environments

## Current Tool Families

- packaging and build metadata
- test and coverage configuration
- linting and type-checking
- docs generation
- security and dependency auditing

## Design Rule

If a setting expresses repository policy or shared workflow, it belongs in
`configs/` or `makes/`, not inside a package root.

If a tool setting exists only to support local package runtime behavior, keep
it with the package.
