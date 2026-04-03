# Packages

This directory contains the publishable Python distributions in the monorepo.

Why `packages/`:

- The repository contains multiple independent distributions, not one shared
  Python package.
- Each distribution keeps its own `src/`, `tests/`, docs, and release metadata.
- Shared tooling stays at the repository root in `configs/` and `makes/`.

This mirrors the role that `crates/` plays in a Rust workspace while preserving
the Python packaging convention of `src/` inside each package.
