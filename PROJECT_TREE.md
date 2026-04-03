# Repository Tree

```text
bijux-llm-nexus/
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
├── CHANGELOG.md
├── LICENSE
├── PROJECT_TREE.md
├── README.md
├── SECURITY.md
├── TESTS.md
├── TOOLING.md
├── USAGE.md
├── .github/
│   └── workflows/
├── configs/
│   ├── shared/
│   └── <package>/
├── docs/
│   └── repository-history.md
├── makes/
│   ├── shared/
│   └── <package>/
└── packages/
    ├── agentic-flows/
    ├── bijux-agent/
    ├── bijux-rag/
    ├── bijux-rar/
    └── bijux-vex/
```

## Layout Rules

- `packages/` contains publishable distributions.
- `.github/workflows/` contains repository-owned automation for each package.
- `configs/` contains repo-owned tool configuration.
- `makes/` contains repo-owned automation fragments.
- root markdown files define repository-wide contracts and contributor guidance.
