# Repository Usage

This repository is organized for package-focused development.

## Explore Packages

- `packages/bijux-canon-runtime`
- `packages/bijux-canon-agent`
- `packages/bijux-canon-ingest`
- `packages/bijux-canon-reason`
- `packages/bijux-canon-index`

## Typical Workflows

Run a package command from the repository root:

```bash
make -C packages/bijux-canon-ingest test
make -C packages/bijux-canon-index docs
```

Inspect shared tooling:

```bash
ls configs
ls makes
```

Read repository history notes:

```bash
sed -n '1,160p' docs/repository-history.md
```
