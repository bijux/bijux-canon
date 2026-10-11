---
title: Documentation Deployment
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-10-11
---

# Documentation Deployment

`deploy-docs.yml` converts the checked-in handbook into a GitHub Pages artifact
and deploys that exact artifact. The workflow keeps toolchain discovery, build,
verification, artifact selection, permissions, and the Pages environment in one
visible custody chain.

```mermaid
flowchart LR
    T[Admitted manual dispatch] --> C[Resolve configuration]
    C --> S[Provision required toolchains]
    S --> B[Run install and build commands]
    B --> R[Resolve site directory]
    R --> V[Verify index and configured checks]
    V --> U[Upload Pages artifact]
    U --> D[Deploy github-pages environment]
```

## Trigger and permission boundary

The workflow supports only `workflow_dispatch` on `refs/heads/main`, with an
explicit `accepted_commit` selected by the authorized publication controller.
The admission job validates the authenticated actor and exact accepted commit
before building. Its product evidence comes from the accepted human pull
request; a dependency notice cannot supply publication readiness.

Repository content is read-only for construction. Pages and identity-token
write permissions belong to the deployment job, which targets the protected
`github-pages` environment and reports the deployed URL. Concurrency is scoped
to the ref, with stale runs canceled.

## Configuration precedence

Deploy settings may come from explicit environment, repository variables, or
`.github/docs-deploy.env`, with built-in defaults last. The resolver determines:

- public site URL and expected site directory;
- install, build, and verification commands;
- Python, Node.js, and Rust versions; and
- whether Python, uv, Node.js, or Rust setup is required.

When commands are not configured, the workflow discovers known Make targets.
It refuses the run if no docs build command can be found. Toolchain detection
uses checked-in project files; it does not install every ecosystem
unconditionally.

## Build and artifact resolution

The configured build receives the public site URL. If no recognizable site is
produced and the repository has MkDocs plus a `docs` target, the workflow makes
one explicit fallback attempt. It then searches the configured directory and a
small set of governed artifact locations.

The selected directory must exist and contain `index.html`. An optional verify
command runs against that exact directory. The Pages bundle is validated again
before `actions/upload-pages-artifact` receives it.

| State | Meaning |
| --- | --- |
| docs build command passed | the configured generator completed |
| site directory resolved | one candidate contains a publishable index |
| verify command passed | repository-specific site checks accepted that candidate |
| Pages artifact uploaded | immutable deploy input exists for this run |
| deploy job passed | GitHub Pages accepted and deployed that artifact |

## Failure interpretation

| Failure | Inspect |
| --- | --- |
| no build command | repository variables, deploy environment, and root Make help |
| no `index.html` | configured output directory and actual MkDocs destination |
| verification failure | `DOCS_SITE_DIR`, generated links, assets, and public URL |
| build passes but deploy skips | trigger type, ref, and build output flag |
| deployment denied | Pages environment and workflow permissions |

## Managed-source boundary

The workflow is a synchronized consumer of the shared `bijux-std` deployment
contract. Repository documentation, MkDocs configuration, and supported deploy
configuration remain local. Changes to workflow mechanics belong upstream;
changes to handbook content and repository-specific build behavior belong here.

The published site is supported only when its source commit, build command,
selected directory, uploaded Pages artifact, and deployment result refer to the
same workflow run.

## Publication documentation environment

`make gh-docs-install` creates the command-owned environment at
`artifacts/root/docs/venv` and synchronizes only the root `docs` dependency group.
It validates `uv.lock` with `uv sync --locked --only-group docs
--no-install-workspace`; application packages, editable workspace distributions
and the root development environment are not installed or replaced. The
standard-library environment is created without bundled pip or virtualenv
startup hooks, so renderer inventories retain explicit installed source ownership.
The repository's existing development groups and package release contexts remain
unchanged. Dependency or plugin changes require an intentional lock review.

`make gh-docs-build` and `make gh-docs-verify` use that same documentation
interpreter. They retain accepted standard source checks, production URL/output
selection, strict rendering, CSP/routes, publication admission and readonly
verification. Installation alone does not qualify a renderer profile or authorize
publication: a new runtime requires actual hosted Linux fingerprints and reviewed
source-owned admission before the publication gate can pass. Unowned environments,
symlinked artifact paths and a stale lock are rejected; command-owned interrupted
creation can resume without deleting unrelated environments or earlier receipts.
