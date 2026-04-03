# Repository Tree

```text
bijux-canon/
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
├── CHANGELOG.md
├── LICENSE
├── README.md
├── SECURITY.md
├── .github/
│   └── workflows/
├── configs/
│   ├── shared/
│   └── <package>/
├── docs/
│   ├── governance.md
│   ├── index.md
│   ├── project-tree.md
│   ├── repository-history.md
│   ├── tests.md
│   ├── tooling.md
│   └── usage.md
├── makes/
│   ├── shared/
│   └── <package>/
└── packages/
    ├── bijux-canon-runtime/
    ├── bijux-canon-agent/
    ├── bijux-canon-ingest/
    ├── bijux-canon-reason/
    ├── bijux-canon-index/
    ├── compat-agentic-flows/
    ├── compat-bijux-agent/
    ├── compat-bijux-rag/
    ├── compat-bijux-rar/
    └── compat-bijux-vex/
```

## Layout Rules

- `packages/` contains publishable distributions.
- `.github/workflows/` contains repository-owned automation for each package.
- `configs/` contains repo-owned tool configuration.
- `docs/` contains repository handbook pages and shared reference material.
- `makes/` contains repo-owned automation fragments.
- root markdown files define repository-wide contracts and contributor guidance.
