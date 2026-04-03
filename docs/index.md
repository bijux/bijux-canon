# bijux-llm-nexus

`bijux-llm-nexus` is a monorepo for independently publishable Python packages
that share repository-wide tooling, governance, and automation.

## Packages

- `packages/agentic-flows`
- `packages/bijux-agent`
- `packages/bijux-llm-rag`
- `packages/bijux-llm-rar`
- `packages/bijux-llm-vex`

## Shared Ownership Model

- package runtime code stays inside each package
- repo-owned tool configuration lives in `configs/`
- repo-owned automation lives in `makes/`
- repository-wide contributor contracts live at the root

## Common Entry Points

Run a package target through the root Makefile:

```bash
make test
make lint PACKAGE=bijux-rag
make docs PACKAGE=bijux-vex
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
