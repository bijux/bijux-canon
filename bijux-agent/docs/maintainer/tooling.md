# Tooling (maintainer)

This repository is intentionally Make-driven so contributors get reproducible commands.

## Bootstrap

```bash
make bootstrap
```

Creates `.venv`, installs dependencies, and installs git hooks (when configured).

## Common targets

```bash
make test
make lint
make docs
make api
make quality
make security
```

List everything:

```bash
make help
```

## Notes

- CI should use the same Make targets as local development.
- If you add a new tool, expose it via a Make target (don’t hide it in CI YAML only).
