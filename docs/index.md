# bijux-canon

`bijux-canon` is a monorepo for independently publishable Python packages
that share repository-wide tooling, governance, and automation.

## Packages

- `packages/bijux-canon-runtime`
- `packages/bijux-canon-agent`
- `packages/bijux-canon-ingest`
- `packages/bijux-canon-reason`
- `packages/bijux-canon-index`

## Shared Ownership Model

- package runtime code stays inside each package
- repo-owned tool configuration lives in `configs/`
- repo-owned automation lives in `makes/`
- repository-wide contributor contracts live at the root

## Common Entry Points

Run a package target through the root Makefile:

```bash
make test
make lint PACKAGE=bijux-canon-ingest
make docs PACKAGE=bijux-canon-index
```

List tox environments from the root:

```bash
tox -av
```

## Next Reads

- [Usage](usage.md)
- [Tests](tests.md)
- [Tooling](tooling.md)
- [Governance](governance.md)
- [Repository History](repository-history.md)
- [Project Tree](project-tree.md)
