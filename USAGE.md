# Repository Usage

This repository is organized for package-focused development.

## Explore Packages

- `packages/agentic-flows`
- `packages/bijux-agent`
- `packages/bijux-rag`
- `packages/bijux-rar`
- `packages/bijux-vex`

## Typical Workflows

Run a package command from the repository root:

```bash
make -C packages/bijux-rag test
make -C packages/bijux-vex docs
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
