# bijux-canon

`bijux-canon` is a contract-first Python system for turning source material
into evidence-bearing, inspectable runs. Five canonical packages separate
preparation, retrieval, reasoning, orchestration, and runtime authority so a
reviewer can identify who made each decision and which artifact supports it.

The project is built for work that must survive review after execution. It
keeps API schemas in the repository, records provenance at retrieval and
reasoning boundaries, emits agent traces, and gives runtime policy the final
authority over persistence and replay. Determinism does not make a model
correct; it makes the execution conditions and resulting evidence inspectable.

<!-- bijux-canon-badges:generated:start -->
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://pypi.org/project/bijux-canon-runtime/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-0F766E)](https://github.com/bijux/bijux-canon/blob/main/LICENSE)
[![Verify](https://github.com/bijux/bijux-canon/actions/workflows/verify.yml/badge.svg?branch=main)](https://github.com/bijux/bijux-canon/actions/workflows/verify.yml?query=branch%3Amain)
[![Release PyPI](https://img.shields.io/badge/release-pypi%20workflow-2563EB?logo=githubactions&logoColor=white)](https://github.com/bijux/bijux-canon/actions/workflows/release-pypi.yml)
[![Release GHCR](https://img.shields.io/badge/release-ghcr%20workflow-2563EB?logo=githubactions&logoColor=white)](https://github.com/bijux/bijux-canon/actions/workflows/release-ghcr.yml)
[![Release GitHub](https://img.shields.io/badge/release-github%20workflow-2563EB?logo=githubactions&logoColor=white)](https://github.com/bijux/bijux-canon/actions/workflows/release-github.yml)
[![Docs](https://github.com/bijux/bijux-canon/actions/workflows/deploy-docs.yml/badge.svg)](https://github.com/bijux/bijux-canon/actions/workflows/deploy-docs.yml)
[![Release](https://img.shields.io/github/v/release/bijux/bijux-canon?display_name=tag&label=release)](https://github.com/bijux/bijux-canon/releases)
[![GHCR packages](https://img.shields.io/badge/ghcr-11%20packages-181717?logo=github)](https://github.com/bijux?tab=packages&repo_name=bijux-canon)
[![Published packages](https://img.shields.io/badge/published%20packages-11-2563EB)](https://github.com/bijux/bijux-canon/tree/main/packages)

[![bijux-canon-runtime](https://img.shields.io/pypi/v/bijux-canon-runtime?label=runtime&logo=pypi)](https://pypi.org/project/bijux-canon-runtime/)
[![bijux-canon](https://img.shields.io/pypi/v/bijux-canon?label=bijux--canon&logo=pypi)](https://pypi.org/project/bijux-canon/)
[![bijux-canon-agent](https://img.shields.io/pypi/v/bijux-canon-agent?label=agent&logo=pypi)](https://pypi.org/project/bijux-canon-agent/)
[![bijux-canon-ingest](https://img.shields.io/pypi/v/bijux-canon-ingest?label=ingest&logo=pypi)](https://pypi.org/project/bijux-canon-ingest/)
[![bijux-canon-reason](https://img.shields.io/pypi/v/bijux-canon-reason?label=reason&logo=pypi)](https://pypi.org/project/bijux-canon-reason/)
[![bijux-canon-index](https://img.shields.io/pypi/v/bijux-canon-index?label=index&logo=pypi)](https://pypi.org/project/bijux-canon-index/)
[![agentic-flows](https://img.shields.io/pypi/v/agentic-flows?label=agentic--flows&logo=pypi)](https://pypi.org/project/agentic-flows/)
[![bijux-agent](https://img.shields.io/pypi/v/bijux-agent?label=bijux--agent&logo=pypi)](https://pypi.org/project/bijux-agent/)
[![bijux-rag](https://img.shields.io/pypi/v/bijux-rag?label=bijux--rag&logo=pypi)](https://pypi.org/project/bijux-rag/)
[![bijux-rar](https://img.shields.io/pypi/v/bijux-rar?label=bijux--rar&logo=pypi)](https://pypi.org/project/bijux-rar/)
[![bijux-vex](https://img.shields.io/pypi/v/bijux-vex?label=bijux--vex&logo=pypi)](https://pypi.org/project/bijux-vex/)

[![bijux-canon-runtime](https://img.shields.io/badge/runtime-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-runtime)
[![bijux-canon](https://img.shields.io/badge/bijux--canon-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon)
[![bijux-canon-agent](https://img.shields.io/badge/agent-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-agent)
[![bijux-canon-ingest](https://img.shields.io/badge/ingest-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-ingest)
[![bijux-canon-reason](https://img.shields.io/badge/reason-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-reason)
[![bijux-canon-index](https://img.shields.io/badge/index-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-index)
[![agentic-flows](https://img.shields.io/badge/agentic--flows-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fagentic-flows)
[![bijux-agent](https://img.shields.io/badge/bijux--agent-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-agent)
[![bijux-rag](https://img.shields.io/badge/bijux--rag-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-rag)
[![bijux-rar](https://img.shields.io/badge/bijux--rar-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-rar)
[![bijux-vex](https://img.shields.io/badge/bijux--vex-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-vex)

[![bijux-canon-runtime docs](https://img.shields.io/badge/docs-runtime-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/06-bijux-canon-runtime/)
[![bijux-canon-agent docs](https://img.shields.io/badge/docs-agent-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/05-bijux-canon-agent/)
[![bijux-canon-ingest docs](https://img.shields.io/badge/docs-ingest-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/02-bijux-canon-ingest/)
[![bijux-canon-reason docs](https://img.shields.io/badge/docs-reason-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/04-bijux-canon-reason/)
[![bijux-canon-index docs](https://img.shields.io/badge/docs-index-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/03-bijux-canon-index/)
<!-- bijux-canon-badges:generated:end -->

## Trust Model

`bijux-canon` narrows claims to the evidence a run actually retains:

| Claim | Evidence required | What that evidence does not prove |
| --- | --- | --- |
| source preparation is repeatable | normalized records, chunk configuration, input identity, and typed failures | that the source itself is correct |
| retrieval is reproducible | execution request, backend capabilities, index identity, ranked results, and provenance | that the most relevant evidence exists in the corpus |
| a claim is supported | exact evidence spans, content digests, claim status, verification report, and reasoning trace | factual truth beyond the registered checks |
| agent work is auditable | ordered role calls, convergence decision, terminal status, and complete trace | that a provider behaved deterministically |
| a run is replayable | manifest, dataset and plan identities, policy, entropy record, finalized trace, and replay envelope | equivalence outside the declared replay boundary |

Missing evidence produces a narrower claim or an explicit refusal. It is not
reconstructed from a plausible final answer.

## Quickstart: Offline Lexical Research

The base Runtime wheel provides the model-free profile. From a release source
archive or repository checkout, run the ancient-DNA workflow against a clean
installed environment:

```bash
python -m venv artifacts/ancient-dna-offline/venv
artifacts/ancient-dna-offline/venv/bin/python -m pip install bijux-canon-runtime

python examples/ancient-dna-research/offline_lexical_workflow.py \
  --runtime-command artifacts/ancient-dna-offline/venv/bin/bijux-canon-runtime \
  --workspace artifacts/ancient-dna-offline/runtime-workspace \
  --evidence-directory artifacts/ancient-dna-offline/evidence
```

This executes discovery, durable ingest, lexical indexing, evidence search,
grounded answering, bounded inspection, process restart, replay, and comparison
through the public Runtime CLI. It requires no model, provider credential, or
optional extra. The final `summary.json` binds the answer and exact citation
locators to the source, corpus, index, configuration, job, run, and replay
identities. See the
[offline ancient-DNA workflow](examples/ancient-dna-research/README.md) for
network-denied release acceptance and manual inspection commands.

For real CPU embeddings, install the `local-cpu` profile, acquire the pinned
MiniLM model once, then run the sibling hybrid workflow. Model acquisition is
the only networked step; validation, ingest, exact and ANN queries, restart,
and the 12-question development evaluation run from retained local bytes:

```bash
python -m venv artifacts/ancient-dna-cpu/venv
artifacts/ancient-dna-cpu/venv/bin/python -m pip install \
  'bijux-canon-runtime[local-cpu]'

artifacts/ancient-dna-cpu/venv/bin/bijux-canon-index model acquire \
  --profile local-minilm-384 \
  --cache-root artifacts/ancient-dna-cpu/models

python examples/ancient-dna-research/cpu_hybrid_workflow.py \
  --runtime-command artifacts/ancient-dna-cpu/venv/bin/bijux-canon-runtime \
  --index-command artifacts/ancient-dna-cpu/venv/bin/bijux-canon-index \
  --model-directory artifacts/ancient-dna-cpu/models/local-minilm-384/1110a243fdf4706b3f48f1d95db1a4f5529b4d41 \
  --workspace artifacts/ancient-dna-cpu/runtime-workspace \
  --evidence-directory artifacts/ancient-dna-cpu/evidence
```

The workflow fails unless exact and ANN retrieval both execute without
fallback, hybrid results retain their lexical and dense contributions, and the
development set clears the frozen 0.90 Recall@5, 0.85 MRR@10, and 0.85
nDCG@10 floors.

This repository defines `11` publishable package records. PyPI, GHCR, and
GitHub Release are independent publication workflows. Each resolves the
checked-in release matrix and invokes the same reusable artifact-building
contract for its own run; destination success must be verified separately.

The six compatibility distributions in this repository are real alias
packages, not migration-only placeholders. Five preserve retired public names,
and one preserves the shorter family-root `bijux-canon` runtime name. All six
re-export canonical package surfaces directly.

## What Works As Shipped

The repository contains substantial package-local implementations, but the
working boundary is not the same for every surface. Use this table before
choosing an example or making an integration claim:

| Capability | Supported entry | Evidence produced | Important limit |
| --- | --- | --- | --- |
| deterministic document preparation and local retrieval | ingest Python, CLI, and HTTP v1 | prepared records, chunk identity, persisted local indexes, ranked candidates, citations | not the governed vector-execution contract owned by index |
| exact or bounded vector execution | index Python, module-invoked CLI, and HTTP v1 | request, capability resolution, execution artifact, provenance, cost, replay comparison | no installed `bijux-canon-index` console script and no runtime contract-enforcement adapter |
| evidence-backed claim construction and verification | reason Python, CLI, and HTTP v1 | claims, support edges, checks, manifests, traces, replay records | verification is scoped to registered evidence and rules; runtime has no reason adapter |
| traced role orchestration | agent Python, CLI, replay, and fixed offline HTTP v1 | ordered calls, lifecycle transitions, convergence and termination records, `RunTrace` | provider determinism is not implied; runtime has no agent adapter |
| manifest resolution, planning, runtime-local policy, storage, inspection, and replay analysis | runtime Python and CLI; HTTP health/readiness | immutable plans, causal traces, stored run projections, arbitration and replay verdicts | HTTP run/replay return `501`; canonical live package adapters are not complete |

The strongest immediately reproducible whole-repository demonstration is
runtime plan mode because it resolves checked-in authority, data, dependency,
entropy, and replay declarations without crossing an unavailable live adapter.
The strongest product demonstrations remain package-local: exercise the
owning package, retain its evidence record, and state the boundary that was not
tested. This is more informative than treating co-installation as integration.

## One System, Five Authorities

```mermaid
flowchart LR
    source["documents and datasets"]
    ingest["ingest<br/>clean, chunk, prepare"]
    index["index<br/>execute and explain retrieval"]
    reason["reason<br/>form and verify claims"]
    agent["agent<br/>coordinate traced work"]
    runtime["runtime<br/>authorize, persist, replay"]
    record["governed run record"]

    source -. ownership handoff .-> ingest
    ingest -. ownership handoff .-> index
    index -. ownership handoff .-> reason
    reason -. ownership handoff .-> agent
    agent -. ownership handoff .-> runtime
    runtime --> record
```

| Authority | Accepts | Produces | Refuses to own |
| --- | --- | --- | --- |
| `bijux-canon-ingest` | source documents and preparation configuration | cleaned records, chunks, local indexes, retrieval-ready material | vector-backend execution policy |
| `bijux-canon-index` | declared vector operations, capabilities, and backend inputs | execution artifacts, provenance-rich results, explanations, replay comparisons | document normalization or claim meaning |
| `bijux-canon-reason` | problems, evidence, retrieval results, and verification rules | claims, checks, manifests, traces, and replayable reasoning runs | workflow choreography or whole-run authority |
| `bijux-canon-agent` | prompts, files, run configuration, and role-specific work | ordered pipeline outcomes and mandatory trace metadata | runtime acceptance and persistence policy |
| `bijux-canon-runtime` | flow manifests, datasets, policies, and lower-layer artifacts | accepted or rejected run records, stored artifacts, replay and diff results | reimplementing lower-package semantics |

The boundaries matter most when something fails. Preparation errors remain
ingest errors; unsupported backend capabilities remain index errors;
insufficient evidence remains a reasoning result; orchestration failures remain
traceable agent outcomes; policy violations remain runtime verdicts. No layer
has to disguise another layer's failure as success.

### Current Composition Boundary

The diagram is an ownership model, not evidence that the installed packages
currently form a turnkey live pipeline. Runtime resolves four integration
callables lazily at execution time, while the corresponding canonical package
roots do not currently publish those callables:

| Runtime integration request | Current canonical root | Consequence |
| --- | --- | --- |
| `bijux_canon_ingest.retrieve` | not exported; the package-local retrieval function also requires an `index_path` rather than runtime's scope and vector-contract arguments | an explicit retrieval adapter is required |
| `bijux_canon_index.enforce_contract` | not exported | runtime cannot use the canonical index root as its vector-contract enforcer |
| `bijux_canon_reason.reason` | not exported | runtime cannot use the canonical reason root as its reasoning runner |
| `bijux_canon_agent.run` | not exported; the root intentionally exposes only `API_VERSION` | runtime cannot use the canonical agent root as its agent runner |

The legacy-module fallbacks are aliases to the same canonical roots, so they do
not supply a missing callable. Package-local Python, CLI, and implemented HTTP
surfaces remain independently usable, and runtime plan mode does not invoke
these adapters. Do not claim supported end-to-end live composition until the
adapter contracts are explicit and an installed-package integration test
exercises them.

## Contract Surfaces

The public contract is larger than Python imports:

- Python distributions and typed root imports provide in-process use.
- Canonical console commands provide automation-friendly entry points for
  ingest, reason, agent, and runtime. Index is an in-process execution library;
  its preserved `bijux-vex` compatibility distribution supplies the historical
  command name.
- Versioned OpenAPI documents under `apis/<package>/v1/` pin HTTP behavior for
  all five canonical packages.
- Package tests cover local semantics; API, invariant, integration, end-to-end,
  and regression suites protect their selected boundaries. The runtime's
  package-root adapter seam is not currently covered by a live canonical-package
  integration test.
- Compatibility distributions preserve six existing names while canonical
  ownership remains with the five `bijux-canon-*` packages.

Start with the owning package instead of installing the entire family by
habit. The packages are independently publishable and intentionally do not
present one catch-all import surface.

### Interface Shape Is Package-Specific

The five authorities share contract principles, not an identical interface
shape:

| Package | Package-root contract | Operational entry points |
| --- | --- | --- |
| ingest | broad, explicitly enumerated preparation primitives and lazily resolved application exports | canonical CLI and versioned HTTP API |
| index | package version only at the root; execution contracts live in named application, core, domain, and infrastructure modules | Python and versioned HTTP API; no renamed canonical console script |
| reason | typed claims, evidence references, plans, traces, checks, validators, and stable hashing helpers | canonical CLI, preserved `bijux-rar` command, and versioned HTTP API |
| agent | deliberately minimal root exposing `API_VERSION` lazily | canonical CLI, workflow modules, and versioned HTTP API |
| runtime | `FlowManifest`, `RunMode`, and `execute_flow` | canonical CLI and versioned HTTP API |

Do not infer an import from a sibling package or from a diagram. Confirm the
owning package's exported names, documented module boundary, command help, or
HTTP schema. A uniform lifecycle does not justify a fabricated uniform facade.

## Install By Responsibility

Install the package that owns the decision your application needs to make:

```bash
python -m pip install bijux-canon-ingest
python -m pip install bijux-canon-index
python -m pip install bijux-canon-reason
python -m pip install bijux-canon-agent
python -m pip install bijux-canon-runtime
```

These are independent distributions, not installation tiers. An ingest-only
application does not need runtime; a retrieval integration can depend on index
without importing agent orchestration. Use `bijux-canon-runtime` when the
application must apply whole-run policy, persist governed records, or compare
replay results.

After installation, inspect the owning public surface before wiring a workflow:

```bash
bijux-canon-ingest --help
bijux-canon-reason --help
bijux-canon-agent --help
bijux-canon-runtime --help
```

For index integrations, begin with the
[index handbook](https://bijux.io/bijux-canon/03-bijux-canon-index/) and its
typed execution contracts. Existing `bijux-vex` automation remains available
through the compatibility package, but new integrations should target
`bijux-canon-index` directly.

## Inspect A Governed Plan

The repository includes a manifest that can be resolved without executing a
provider, retrieval adapter, reasoning adapter, or agent workflow. This is the
safest concrete starting point for understanding runtime authority:

```bash
uv sync --frozen
uv run bijux-canon-runtime plan \
  packages/bijux-canon-runtime/examples/boring/flow.json \
  --json
```

The resulting plan records the flow and tenant, frozen dataset identity,
ordered steps, determinism level, entropy budget, replay envelope,
environment fingerprint, and `plan_hash`. It does not allocate a run ID,
persist a trace, or establish that the four live package adapters are
callable. That distinction is useful: planning proves that declared authority
can be normalized into an immutable execution contract without confusing that
contract with execution.

Read the output in this order:

1. confirm `flow_id`, `tenant_id`, and the dataset hash identify the intended
   authority boundary;
2. inspect every resolved step and dependency before trusting execution order;
3. verify the determinism and entropy declarations match the intended replay
   claim; and
4. retain `plan_hash` as the identity against which later execution or replay
   evidence must be compared.

The example manifest is deliberately uneventful. It demonstrates admission
and planning, not model quality or end-to-end live composition. Continue with
the [runtime entrypoint guide](https://bijux.io/bijux-canon/06-bijux-canon-runtime/interfaces/entrypoints-and-examples/)
before granting execution authority.

## Read The Repository By Ownership

| If the question is about | Start here | Proof usually lives in |
| --- | --- | --- |
| cross-package rules, shared repository boundaries, or docs routing | [repository handbook](https://bijux.io/bijux-canon/) | `mkdocs.yml`, `pyproject.toml`, `Makefile`, `makes/`, `.github/workflows/` |
| product behavior in one canonical layer | the owning canonical package handbook in the `02` through `06` handbook sections | `packages/<package>/src`, `packages/<package>/tests`, `apis/` |
| maintainer automation, release posture, or repository health | [maintenance handbook](https://bijux.io/bijux-canon/07-bijux-canon-maintain/) | `packages/bijux-canon-dev`, `makes/`, `.github/workflows/` |
| older or shorter compatibility names | [compatibility handbook](https://bijux.io/bijux-canon/08-compat-packages/) | `packages/compat-*`, migration docs, package metadata |

## Repository Consolidation

The package family now ships from a single repository:

- canonical repository: [bijux-canon repository](https://github.com/bijux/bijux-canon)
- migration handbook: [Migration guidance](https://bijux.io/bijux-canon/08-compat-packages/migration/migration-guidance/)
- repository consolidation notes: [Repository consolidation notes](https://bijux.io/bijux-canon/08-compat-packages/migration/repository-consolidation/)

The following standalone repositories are being retired in favor of the
consolidated `bijux-canon` source of truth:

- `bijux/agentic-flows` -> `bijux-canon-runtime`
- `bijux/bijux-agent` -> `bijux-canon-agent`
- `bijux/bijux-rag` -> `bijux-canon-ingest`
- `bijux/bijux-rar` -> `bijux-canon-reason`
- `bijux/bijux-vex` -> `bijux-canon-index`

The repository also ships `bijux-canon` as a shorter compatibility
distribution for `bijux-canon-runtime`. It is a real alias package, not a
retired standalone repository.

## Engineering Commitments

- **Contracts are checked in.** The OpenAPI source, pinned representation, and
  schema hash for each canonical HTTP API are versioned under `apis/`.
- **Replay has preconditions.** A replay claim depends on declared contracts,
  captured inputs, stable identifiers, and the package's documented
  determinism boundary.
- **Failures retain ownership.** Packages expose typed failures and validation
  outcomes rather than silently coercing invalid work into plausible output.
- **Compatibility is observable.** Legacy distributions, imports, and commands
  are implemented as explicit alias packages with canonical targets.
- **Release custody is explicit.** Each destination records its source SHA,
  package matrix, named staged artifact, permissions, and publication result.

## Release Custody

```mermaid
flowchart LR
    source["source SHA + release matrix"]
    builder["reusable artifact builder"]
    pypi["PyPI workflow"]
    ghcr["GHCR workflow"]
    github["GitHub Release workflow"]
    pd["package-pypi-dist"]
    rd["package-release"]

    source --> pypi --> builder --> pd
    source --> ghcr --> builder --> rd
    source --> github --> builder --> rd
```

There is no repository-local workflow that atomically publishes all three
destinations. Each destination builds from its workflow run, consumes the
named artifact produced in that run, and reports its own result. A PyPI success
does not establish GHCR or GitHub Release success, and registry acceptance does
not by itself prove downstream installation or SBOM validity.

The [release workflow handbook](https://bijux.io/bijux-canon/07-bijux-canon-maintain/gh-workflows/release-workflows/)
documents inputs, artifact names, authentication, permissions, and refusal
behavior for each destination.

## Package Map

The 11 publishable packages in this repository are:

| Package | Purpose | Links |
| --- | --- | --- |
| `bijux-canon-runtime` | Governed execution, policy enforcement, and replay | <a href="https://pypi.org/project/bijux-canon-runtime/"><img alt="PyPI" src="https://img.shields.io/badge/pypi-3775A9?logo=pypi&logoColor=white" height="18"></a> <a href="https://bijux.io/bijux-canon/06-bijux-canon-runtime/"><img alt="Docs" src="https://img.shields.io/badge/docs-2563EB?logo=materialformkdocs&logoColor=white" height="18"></a> <a href="https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-runtime"><img alt="GHCR" src="https://img.shields.io/badge/ghcr-181717?logo=github&logoColor=white" height="18"></a> <a href="https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-runtime"><img alt="Source" src="https://img.shields.io/badge/source-181717?logo=github&logoColor=white" height="18"></a> |
| `bijux-canon` | Compatibility package for `bijux-canon-runtime` | <a href="https://pypi.org/project/bijux-canon/"><img alt="PyPI" src="https://img.shields.io/badge/pypi-3775A9?logo=pypi&logoColor=white" height="18"></a> <a href="https://bijux.io/bijux-canon/08-compat-packages/catalog/bijux-canon/"><img alt="Docs" src="https://img.shields.io/badge/docs-2563EB?logo=materialformkdocs&logoColor=white" height="18"></a> <a href="https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon"><img alt="GHCR" src="https://img.shields.io/badge/ghcr-181717?logo=github&logoColor=white" height="18"></a> <a href="https://github.com/bijux/bijux-canon/tree/main/packages/compat-bijux-canon"><img alt="Source" src="https://img.shields.io/badge/source-181717?logo=github&logoColor=white" height="18"></a> |
| `bijux-canon-agent` | Deterministic agent orchestration and execution surfaces | <a href="https://pypi.org/project/bijux-canon-agent/"><img alt="PyPI" src="https://img.shields.io/badge/pypi-3775A9?logo=pypi&logoColor=white" height="18"></a> <a href="https://bijux.io/bijux-canon/05-bijux-canon-agent/"><img alt="Docs" src="https://img.shields.io/badge/docs-2563EB?logo=materialformkdocs&logoColor=white" height="18"></a> <a href="https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-agent"><img alt="GHCR" src="https://img.shields.io/badge/ghcr-181717?logo=github&logoColor=white" height="18"></a> <a href="https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-agent"><img alt="Source" src="https://img.shields.io/badge/source-181717?logo=github&logoColor=white" height="18"></a> |
| `bijux-canon-ingest` | Deterministic ingest, chunking, indexing, and retrieval preparation | <a href="https://pypi.org/project/bijux-canon-ingest/"><img alt="PyPI" src="https://img.shields.io/badge/pypi-3775A9?logo=pypi&logoColor=white" height="18"></a> <a href="https://bijux.io/bijux-canon/02-bijux-canon-ingest/"><img alt="Docs" src="https://img.shields.io/badge/docs-2563EB?logo=materialformkdocs&logoColor=white" height="18"></a> <a href="https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-ingest"><img alt="GHCR" src="https://img.shields.io/badge/ghcr-181717?logo=github&logoColor=white" height="18"></a> <a href="https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-ingest"><img alt="Source" src="https://img.shields.io/badge/source-181717?logo=github&logoColor=white" height="18"></a> |
| `bijux-canon-reason` | Contract-driven reasoning runtime and run artifacts | <a href="https://pypi.org/project/bijux-canon-reason/"><img alt="PyPI" src="https://img.shields.io/badge/pypi-3775A9?logo=pypi&logoColor=white" height="18"></a> <a href="https://bijux.io/bijux-canon/04-bijux-canon-reason/"><img alt="Docs" src="https://img.shields.io/badge/docs-2563EB?logo=materialformkdocs&logoColor=white" height="18"></a> <a href="https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-reason"><img alt="GHCR" src="https://img.shields.io/badge/ghcr-181717?logo=github&logoColor=white" height="18"></a> <a href="https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-reason"><img alt="Source" src="https://img.shields.io/badge/source-181717?logo=github&logoColor=white" height="18"></a> |
| `bijux-canon-index` | Contract-driven vector execution and audited retrieval | <a href="https://pypi.org/project/bijux-canon-index/"><img alt="PyPI" src="https://img.shields.io/badge/pypi-3775A9?logo=pypi&logoColor=white" height="18"></a> <a href="https://bijux.io/bijux-canon/03-bijux-canon-index/"><img alt="Docs" src="https://img.shields.io/badge/docs-2563EB?logo=materialformkdocs&logoColor=white" height="18"></a> <a href="https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-index"><img alt="GHCR" src="https://img.shields.io/badge/ghcr-181717?logo=github&logoColor=white" height="18"></a> <a href="https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-index"><img alt="Source" src="https://img.shields.io/badge/source-181717?logo=github&logoColor=white" height="18"></a> |
| `agentic-flows` | Compatibility package for `bijux-canon-runtime` | <a href="https://pypi.org/project/agentic-flows/"><img alt="PyPI" src="https://img.shields.io/badge/pypi-3775A9?logo=pypi&logoColor=white" height="18"></a> <a href="https://bijux.io/bijux-canon/08-compat-packages/catalog/agentic-flows/"><img alt="Docs" src="https://img.shields.io/badge/docs-2563EB?logo=materialformkdocs&logoColor=white" height="18"></a> <a href="https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fagentic-flows"><img alt="GHCR" src="https://img.shields.io/badge/ghcr-181717?logo=github&logoColor=white" height="18"></a> <a href="https://github.com/bijux/bijux-canon/tree/main/packages/compat-agentic-flows"><img alt="Source" src="https://img.shields.io/badge/source-181717?logo=github&logoColor=white" height="18"></a> |
| `bijux-agent` | Compatibility package for `bijux-canon-agent` | <a href="https://pypi.org/project/bijux-agent/"><img alt="PyPI" src="https://img.shields.io/badge/pypi-3775A9?logo=pypi&logoColor=white" height="18"></a> <a href="https://bijux.io/bijux-canon/08-compat-packages/catalog/bijux-agent/"><img alt="Docs" src="https://img.shields.io/badge/docs-2563EB?logo=materialformkdocs&logoColor=white" height="18"></a> <a href="https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-agent"><img alt="GHCR" src="https://img.shields.io/badge/ghcr-181717?logo=github&logoColor=white" height="18"></a> <a href="https://github.com/bijux/bijux-canon/tree/main/packages/compat-bijux-agent"><img alt="Source" src="https://img.shields.io/badge/source-181717?logo=github&logoColor=white" height="18"></a> |
| `bijux-rag` | Compatibility package for `bijux-canon-ingest` | <a href="https://pypi.org/project/bijux-rag/"><img alt="PyPI" src="https://img.shields.io/badge/pypi-3775A9?logo=pypi&logoColor=white" height="18"></a> <a href="https://bijux.io/bijux-canon/08-compat-packages/catalog/bijux-rag/"><img alt="Docs" src="https://img.shields.io/badge/docs-2563EB?logo=materialformkdocs&logoColor=white" height="18"></a> <a href="https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-rag"><img alt="GHCR" src="https://img.shields.io/badge/ghcr-181717?logo=github&logoColor=white" height="18"></a> <a href="https://github.com/bijux/bijux-canon/tree/main/packages/compat-bijux-rag"><img alt="Source" src="https://img.shields.io/badge/source-181717?logo=github&logoColor=white" height="18"></a> |
| `bijux-rar` | Compatibility package for `bijux-canon-reason` | <a href="https://pypi.org/project/bijux-rar/"><img alt="PyPI" src="https://img.shields.io/badge/pypi-3775A9?logo=pypi&logoColor=white" height="18"></a> <a href="https://bijux.io/bijux-canon/08-compat-packages/catalog/bijux-rar/"><img alt="Docs" src="https://img.shields.io/badge/docs-2563EB?logo=materialformkdocs&logoColor=white" height="18"></a> <a href="https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-rar"><img alt="GHCR" src="https://img.shields.io/badge/ghcr-181717?logo=github&logoColor=white" height="18"></a> <a href="https://github.com/bijux/bijux-canon/tree/main/packages/compat-bijux-rar"><img alt="Source" src="https://img.shields.io/badge/source-181717?logo=github&logoColor=white" height="18"></a> |
| `bijux-vex` | Compatibility package for `bijux-canon-index` | <a href="https://pypi.org/project/bijux-vex/"><img alt="PyPI" src="https://img.shields.io/badge/pypi-3775A9?logo=pypi&logoColor=white" height="18"></a> <a href="https://bijux.io/bijux-canon/08-compat-packages/catalog/bijux-vex/"><img alt="Docs" src="https://img.shields.io/badge/docs-2563EB?logo=materialformkdocs&logoColor=white" height="18"></a> <a href="https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-vex"><img alt="GHCR" src="https://img.shields.io/badge/ghcr-181717?logo=github&logoColor=white" height="18"></a> <a href="https://github.com/bijux/bijux-canon/tree/main/packages/compat-bijux-vex"><img alt="Source" src="https://img.shields.io/badge/source-181717?logo=github&logoColor=white" height="18"></a> |

Repository-owned developer tooling also lives here in
[`packages/bijux-canon-dev`](packages/bijux-canon-dev), but it is for
maintaining the workspace rather than for end-user installation.

## Choose By The Decision You Need To Review

| Decision under review | Canonical package | First evidence to inspect |
| --- | --- | --- |
| how bytes became normalized records and chunks | `bijux-canon-ingest` | prepared records, configuration, and input identity |
| why a backend accepted, refused, or ranked a vector request | `bijux-canon-index` | `ExecutionRequest`, capabilities, and `ExecutionArtifact` provenance |
| how evidence became a claim | `bijux-canon-reason` | support references, content hashes, trace, and verification report |
| why a role ran and how the workflow terminated | `bijux-canon-agent` | `PipelineDefinition`, `PipelineResult`, and versioned `RunTrace` |
| whether the complete run may be retained or replayed | `bijux-canon-runtime` | `FlowManifest`, policy, finalized trace, and replay verdict |

The [published handbook](https://bijux.io/bijux-canon/) follows the same
ownership map. Use the [compatibility handbook](docs/08-compat-packages/index.md)
only for preserved distribution, import, submodule, or command names; current
behavior belongs to the canonical package.

## Verify A Claim

The repository keeps four proof surfaces separate:

- `packages/<package>/src` implements package behavior;
- `packages/<package>/tests` exercises local and cross-boundary invariants;
- `apis/<package>/v1` records the versioned HTTP schema, pinned representation,
  and hash; and
- run artifacts record what happened in one execution.

None substitutes for the others. A checked-in schema does not prove its server
is implemented, a passing unit test does not make a scientific claim true, and
a completed run does not establish replay without its identities and policy.

## Work With The Repository

All transient local outputs belong under `artifacts/`. The root verification
environment belongs under `artifacts/root/check-venv/`, and a locally rendered
documentation site belongs under `artifacts/root/docs/site/`. These paths are
disposable execution products; checked-in schemas, handbooks, and release
metadata remain in their governed repository locations.

- Read the [documentation map](docs/index.md) for package and evidence routing.
- Browse [packages](packages) for canonical and compatibility distributions.
- Browse [API contracts](apis) for checked-in HTTP schemas.
- Run `make help` for the supported local command surface.
- Run `make docs-check` for the strict documentation build.
- Read [CONTRIBUTING.md](CONTRIBUTING.md) before proposing a change.

## License

This repository is licensed under the Apache License 2.0. Copyright 2026 Bijan Mousavi <bijan@bijux.io>. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).
