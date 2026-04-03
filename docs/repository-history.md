# Repository History Map

This repository preserves the standalone history of each imported project.

Layout:

- `agentic-flows/`
- `bijux-agent/`
- `bijux-rag/`
- `bijux-rar/`
- `bijux-vex/`

History model:

- Each project was imported with a subtree merge so the original commit graph
  remains reachable from the monorepo history.
- Original default branch tips are preserved as `archive/<project>/main`.
- Original documentation branch tips are preserved as
  `archive/<project>/gh-pages`.
- Release tags are namespaced as `<project>/vX.Y.Z` to avoid collisions across
  packages that shared the same version numbers.

Examples:

- `archive/bijux-rag/main`
- `archive/bijux-rag/gh-pages`
- `bijux-rag/v0.1.0`
- `agentic-flows/v0.1.1`
