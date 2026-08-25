---
title: Version 0.4.0 Release Candidate
audience: mixed
type: how-to
status: candidate
owner: bijux-canon-release
last_reviewed: 2026-08-25
---

# Version 0.4.0 Release Candidate

Version 0.4.0 is the first release candidate that treats the installed Python
distribution family, durable runtime state, research evidence, evaluation
truth, and release evidence as one product boundary. This page is the
candidate-derived release note, upgrade guide, publication runbook, and
rollback record. It describes shipped and tested behavior; it does not confer
publication approval.

The candidate contains twelve same-version Python distributions: five
canonical product packages, six compatibility packages, and the internal
`bijux-canon-dev` verifier package. Eleven are public release artifacts.
`bijux-canon-dev` is built and inspected with the family but is not uploaded as
part of the public publication matrix.

## Distribution Notes and Install Profiles

All distributions require Python `>=3.11,<4`. Use exact `==0.4.0` pins for a
release installation. The compatibility names delegate to the named canonical
owner; they do not contain an independent implementation.

| Distribution | 0.4.0 shipped behavior | Supported install profile | Migration and limitation |
| --- | --- | --- | --- |
| `bijux-canon-ingest` | Provenance-bound corpus preparation, semantic chunks, stable locators, incremental snapshots, and bounded PDF, DOCX, OCR, archive, and discovery handling | `bijux-canon-ingest==0.4.0`; `[docs]` is documentation tooling, not a runtime parser profile | Rebuild derived snapshots when parser or chunk-policy identity changes; malformed, oversized, encrypted, or unsupported input is rejected rather than guessed |
| `bijux-canon-index` | Immutable lexical, exact-vector, ANN, and hybrid generations; installed model acquire/register/validate; qrel evaluation and tamper checks | base for lexical; `[config]`; `[api]`; `[embeddings]`; `[local-cpu]`; `[nd]`; `[vdb]` | Pin and validate model revision, files, license, dimension, and backend compatibility before dense use; `local-cpu` is the verified workstation profile |
| `bijux-canon-reason` | Evidence projection, claim qualification, contradiction handling, citation verification, abstention, and bounded provider synthesis | base for local reasoning; `[api]`; `[bench]` | Irrelevant or insufficient evidence now abstains; callers must not treat an answer string as proof without its claim and citation verdicts |
| `bijux-canon-agent` | Requirement-targeted research planning, governed tool execution, bounded concurrency, convergence, cancellation, and retained outcomes | base; `[api]` for HTTP integration; `[env]` for dotenv loading | Provider credentials are lazy and tool output remains untrusted data; incomplete work is an explicit outcome, not an implicit success |
| `bijux-canon-runtime` | Runtime v2 CLI/HTTP application services, durable jobs, immutable run publication, replay, comparison, inspection, recovery, and profile-aware readiness | base `offline-lexical`; `[api]` for the HTTP server; `[local-cpu]` for exact, ANN, and hybrid local retrieval | Workspace format 5 migrates format 4 with a verified backup; direct relocation incompatibility is explicit; v1 run/replay is deprecated |
| `bijux-canon-dev` | Installed wheel, installation, extras, Python, family, semver, secret, unfinished-marker, resource, supply-chain, and candidate verifiers | base for release verification; `[dev]` only for repository development | Internal support distribution; build and validate it with the family but do not add it to the eleven-package public upload matrix |
| `bijux-canon` | Exact-version compatibility distribution for `bijux-canon-runtime` | `bijux-canon==0.4.0` | Deprecated in 0.4.0; migrate distribution, `bijux_canon` imports, and `bijux-canon` command to runtime before 1.0.0 |
| `agentic-flows` | Exact-version compatibility distribution for `bijux-canon-runtime` | `agentic-flows==0.4.0` | Deprecated in 0.4.0; migrate distribution, `agentic_flows` imports, and `agentic-flows` command to runtime before 1.0.0 |
| `bijux-agent` | Exact-version compatibility distribution for `bijux-canon-agent` | `bijux-agent==0.4.0` | Deprecated in 0.4.0; migrate distribution, `bijux_agent` imports, and `bijux-agent` command before 1.0.0 |
| `bijux-rag` | Exact-version compatibility distribution for `bijux-canon-ingest` | `bijux-rag==0.4.0` | Deprecated in 0.4.0; migrate distribution, `bijux_rag` imports, and `bijux-rag` command before 1.0.0 |
| `bijux-rar` | Exact-version compatibility distribution for `bijux-canon-reason` | `bijux-rar==0.4.0` | Deprecated in 0.4.0; migrate distribution, `bijux_rar` imports, and `bijux-rar` command before 1.0.0 |
| `bijux-vex` | Exact-version compatibility distribution for `bijux-canon-index` | `bijux-vex==0.4.0` | Deprecated in 0.4.0; migrate distribution, `bijux_vex` imports, and `bijux-vex` command before 1.0.0 |

Development and documentation extras are maintained contributor profiles. They
are exercised by the extras verifier, but they are not a recommendation for a
production application environment.

## Breaking and Deprecated Behavior

The comparison against tag `v0.3.9` found no removed public package-root
exports, console scripts, or v1 OpenAPI operations, required parameters,
response codes, component schemas, or required fields. Version 0.4.0 is still a
meaningful operational migration:

- the runtime requires the four canonical peer packages at exactly `0.4.0`;
  mixed 0.3.9/0.4.0 product families are unsupported and intentionally fail
  dependency resolution;
- workspace format 5 changes durable runtime state and requires the migration
  and rollback sequence below;
- Runtime v2 is the primary executable run, replay, comparison, inspection,
  cancellation, and recovery contract;
- Runtime v1 run and replay remain available but are deprecated from 0.4.0 and
  will not be removed before 1.0.0; and
- all six compatibility distribution/import/command surfaces are deprecated
  from 0.4.0 and will not be removed before 1.0.0.

Do not infer arbitrary private-module compatibility from this result. The
verified contract covers declared public roots, installed entry points, the
versioned HTTP schemas, and real workspace migration and rollback scenarios.

## Upgrade Procedure

Back up each workspace before changing the installed family. Record the active
generation, configuration identity, and the exact old package set:

```bash
python -m pip freeze > artifacts/release-v0.4.0/pre-upgrade-packages.txt
export BIJUX_CANON_RUNTIME_WORKING_ROOT=/srv/bijux/workspace
bijux-canon-runtime v2 backup pre-upgrade-0.4.0 \
  > artifacts/release-v0.4.0/pre-upgrade-backup.json
bijux-canon-runtime v2 capabilities \
  > artifacts/release-v0.4.0/pre-upgrade-capabilities.json
bijux-canon-runtime v2 ready \
  --operation initialized \
  > artifacts/release-v0.4.0/pre-upgrade-readiness.json
```

Upgrade the complete canonical family in one resolver transaction. Choose one
runtime profile; do not install dense dependencies for an offline lexical
deployment:

```bash
# Offline lexical deployment.
python -m pip install --upgrade \
  'bijux-canon-runtime==0.4.0' \
  'bijux-canon-agent==0.4.0' \
  'bijux-canon-ingest==0.4.0' \
  'bijux-canon-reason==0.4.0' \
  'bijux-canon-index==0.4.0'

# Local CPU exact, ANN, and hybrid deployment.
python -m pip install --upgrade \
  'bijux-canon-runtime[local-cpu]==0.4.0' \
  'bijux-canon-agent==0.4.0' \
  'bijux-canon-ingest==0.4.0' \
  'bijux-canon-reason==0.4.0' \
  'bijux-canon-index[local-cpu]==0.4.0'
```

On Linux CPU hosts, install PyTorch from its CPU wheel index before the local
CPU profile so the resolver does not select CUDA runtime packages. Validate the
pinned model offline before submitting dense work. Then migrate and inspect the
workspace through the runtime command; retain the generated rollback backup:

```bash
python -m pip check
bijux-canon-runtime init \
  --workspace "$BIJUX_CANON_RUNTIME_WORKING_ROOT" \
  --json > artifacts/release-v0.4.0/workspace-migration.json
bijux-canon-runtime v2 ready \
  --operation run \
  --profile offline-lexical \
  > artifacts/release-v0.4.0/post-upgrade-readiness.json
bijux-canon-runtime v2 capabilities \
  > artifacts/release-v0.4.0/post-upgrade-capabilities.json
```

Replace compatibility requirements, imports, command names, configuration,
and automation with canonical owners. Preserve compatibility packages only
while a named consumer still needs them, and test that consumer both with the
bridge and with the canonical package alone.

## Candidate Verification Record

All release evidence must refer to one clean candidate commit and one freshly
built set of twelve wheels and twelve source distributions. Store generated
records below `artifacts/release-v0.4.0/`. A development-version wheel set or a
result from an earlier commit is diagnostic evidence, not the final candidate
record.

Build the candidate exactly once from the clean approved commit. The explicit
version override is for pre-tag candidate construction only; after tag
approval, the tag itself must resolve the same stable version:

Use CPython 3.11 as the governed artifact-construction interpreter. The later
Python support matrix installs the resulting interpreter-independent wheels on
every declared Python version.

```bash
test ! -e artifacts/release-v0.4.0/dist
mkdir -p artifacts/release-v0.4.0/dist
export SETUPTOOLS_SCM_PRETEND_VERSION=0.4.0
for BIJUX_PACKAGE_DIR in \
  packages/bijux-canon-agent \
  packages/bijux-canon-dev \
  packages/bijux-canon-index \
  packages/bijux-canon-ingest \
  packages/bijux-canon-reason \
  packages/bijux-canon-runtime \
  packages/compat-agentic-flows \
  packages/compat-bijux-agent \
  packages/compat-bijux-canon \
  packages/compat-bijux-rag \
  packages/compat-bijux-rar \
  packages/compat-bijux-vex
do
  uv run --frozen --python 3.11 python -m build \
    --wheel \
    --sdist \
    --outdir artifacts/release-v0.4.0/dist \
    "$BIJUX_PACKAGE_DIR"
done
unset SETUPTOOLS_SCM_PRETEND_VERSION
test "$(find artifacts/release-v0.4.0/dist -name '*.whl' | wc -l)" -eq 12
test "$(find artifacts/release-v0.4.0/dist -name '*.tar.gz' | wc -l)" -eq 12
```

Create the current Python dependency wheelhouse from the frozen lock. Preserve
the exported requirements and wheel hashes with the candidate:

```bash
mkdir -p artifacts/release-v0.4.0/dependency-wheels
uv export \
  --frozen \
  --all-packages \
  --all-extras \
  --no-dev \
  --no-emit-workspace \
  --format requirements.txt \
  --output-file artifacts/release-v0.4.0/dependency-requirements.txt
uv run --frozen --python 3.11 python -m pip download \
  --requirement artifacts/release-v0.4.0/dependency-requirements.txt \
  --destination-directory artifacts/release-v0.4.0/dependency-wheels
```

Run the deduplicated frozen graph once and let it continue in the background
while independent read-only evidence is reviewed:

```bash
make candidate-frozen
make frozen-status GATE=candidate
make frozen-summary GATE=candidate
```

For the exact candidate artifacts, require successful results from these
installed commands and retain their JSON outputs:

```bash
bijux-canon-wheel-inventory \
  --repo-root . \
  --wheel-dir artifacts/release-v0.4.0/dist \
  --output artifacts/release-v0.4.0/wheel-inventory.json

bijux-canon-installation-matrix \
  --repo-root . \
  --wheel-dir artifacts/release-v0.4.0/dist \
  --dependency-wheel-dir artifacts/release-v0.4.0/dependency-wheels \
  --environment-root artifacts/release-v0.4.0/installations \
  --output artifacts/release-v0.4.0/installation-matrix.json

bijux-canon-extras-matrix \
  --repo-root . \
  --wheel-dir artifacts/release-v0.4.0/dist \
  --dependency-wheel-dir artifacts/release-v0.4.0/dependency-wheels \
  --environment-root artifacts/release-v0.4.0/extras \
  --output artifacts/release-v0.4.0/extras-matrix.json

bijux-canon-python-support \
  --repo-root . \
  --wheel-dir artifacts/release-v0.4.0/dist \
  --environment-root artifacts/release-v0.4.0/python-support \
  --output artifacts/release-v0.4.0/python-support.json

bijux-canon-family-compatibility \
  --repo-root . \
  --wheel-dir artifacts/release-v0.4.0/dist \
  --dependency-wheel-dir artifacts/release-v0.4.0/dependency-wheels \
  --environment-root artifacts/release-v0.4.0/family \
  --output artifacts/release-v0.4.0/family-compatibility.json \
  --previous-version 0.3.9 \
  --python-version 3.11
```

Run `make security` without vulnerability ignores, run the tracked-source
secret scan, and pass all twelve strict audit reports plus the secret report to
`bijux-canon-supply-chain`. The supply-chain result must bind each wheel and
source distribution, its CycloneDX SBOM, source commit, locks, build
environment, `LICENSE`, `NOTICE`, corpus locks, corpus manifests, acquisition
receipts, and reviewed security evidence.

The candidate corpus acknowledgement is not a claim of ownership over source
publications. Ancient-DNA and urban-heat examples retain exact source URLs,
licenses, acquisition receipts, content hashes, corpus locks, manifests, and
question/claim/citation truth. Redistributed document-format fixtures retain
their governing manifest and license classification. Any changed corpus byte
requires renewed admission and truth review.

Immediately before approval, refresh the live read-only registry preflight:

```bash
bijux-canon-release-candidate \
  --repo-root . \
  --wheel-dir artifacts/release-v0.4.0/dist \
  --output artifacts/release-v0.4.0/registry-preflight.json \
  --tag v0.4.0 \
  --github-repository bijux/bijux-canon \
  --remote origin
```

The candidate is not approval-ready unless the frozen graph, installed
product matrices, development and held-out evaluation decisions, CI-required
product checks, supply-chain review, documentation build, and live registry
preflight all refer to the same clean commit and pass.

## Known Limitations

- Version 0.4.0 ships Python distributions only. GHCR assets are
  non-executable distribution bundles; no runnable service image is promised.
- Local provenance is unsigned. It binds bytes and inputs but does not provide
  trusted remote-builder identity, key custody, or transparency-log proof.
- Local CPU resource ceilings were calibrated on an Apple M1 Max workstation.
  The `offline-lexical` and `local-cpu-hybrid` profiles passed those governed
  ceilings, but that result is not a universal latency or throughput promise.
- Supported Python verification covers Python 3.11 through 3.14. A local run
  records one operating system; multi-platform enforcement remains a remote CI
  responsibility.
- Retrieved text is untrusted, model/provider output is fallible, and semantic
  scoring cannot establish real-world truth. Claim and citation verdicts,
  abstention, retained traces, and independent truth review remain required.
- OCR, external providers, hosted vector stores, and HTTP deployment add
  binaries, credentials, network, retention, and operational controls beyond
  the offline lexical boundary.
- Compatibility packages preserve declared public and representative nested
  surfaces during migration; they do not promise every historical private
  module or undocumented behavior.

## Publication Order and Approval Gate

No command in this section is authorized by candidate verification alone.
Creating `v0.4.0`, pushing it, dispatching release workflows, uploading to
PyPI/GHCR, or creating a GitHub Release requires explicit external approval.

After approval, publish the eleven public distributions in the dependency
tiers declared by `pyproject.toml`:

1. `bijux-canon-agent`, `bijux-canon-ingest`, `bijux-canon-reason`, and
   `bijux-canon-index`;
2. `bijux-canon-runtime`, `bijux-agent`, `bijux-rag`, `bijux-rar`, and
   `bijux-vex`; and
3. `bijux-canon` and `agentic-flows`.

Do not publish `bijux-canon-dev`. Do not begin a later tier until every package
in the prior tier is queryable at version 0.4.0 and its registry digest matches
the approved artifact. Stage GitHub Release assets and non-executable GHCR
bundles from the same approved artifact set. Never rebuild between tiers.

The managed release matrices and required status checks must cover this exact
eleven-package set and the same product/release responsibilities as the local
candidate graph before tag creation. A configuration-only green status or a
matrix that omits a public distribution is a publication blocker.

## Rollback Triggers and Procedure

Stop publication or deployment when any of these occurs:

- registry digest, wheel/sdist inventory, `RECORD`, SBOM, attestation, source
  commit, or version differs from the approved candidate;
- any tier package is missing while a dependent tier has begun;
- clean installation, import, entry-point, migration, replay, readiness,
  citation, security, or held-out acceptance fails;
- workspace migration cannot preserve the prior verified generation and
  rollback backup; or
- secrets, vulnerable dependencies, corrupt state, resource-envelope breaches,
  or unexplained evaluation regressions appear.

PyPI files and Git tags are immutable release identities; do not overwrite or
delete them as a routine rollback. Stop later tiers, mark the GitHub Release as
not approved for use, preserve all evidence, and prepare a new patch version.
For deployments, stop writers, restore the pre-upgrade workspace backup into a
fresh location, reinstall the exact 0.3.9 package set recorded before upgrade,
run `python -m pip check`, inspect the restored generation, replay a known run,
and only then redirect traffic.

## Post-Release Checks

After all tiers and release assets are visible, install from the public index
into a new environment without the source checkout and verify exact metadata,
imports, commands, workspace lifecycle, and registry identities:

```bash
python -m venv artifacts/release-v0.4.0/public-install
artifacts/release-v0.4.0/public-install/bin/python -m pip install \
  'bijux-canon-runtime==0.4.0'
artifacts/release-v0.4.0/public-install/bin/python -m pip check
artifacts/release-v0.4.0/public-install/bin/bijux-canon-runtime --help
artifacts/release-v0.4.0/public-install/bin/bijux-canon-runtime init \
  --workspace artifacts/release-v0.4.0/public-workspace \
  --json
BIJUX_CANON_RUNTIME_WORKING_ROOT=artifacts/release-v0.4.0/public-workspace \
  artifacts/release-v0.4.0/public-install/bin/bijux-canon-runtime v2 ready \
    --operation run \
    --profile offline-lexical
```

Query PyPI for all eleven exact versions, verify GitHub Release asset hashes and
the `v0.4.0` commit, verify each GHCR bundle digest where configured, and build
the published documentation. Retain the command output, registry URLs, digests,
timestamps, and environment identity under the release acceptance record.

See [Release and Versioning](release-and-versioning.md),
[Release Support](../../07-bijux-canon-maintain/bijux-canon-dev/release-support.md),
[SBOM and Supply Chain](../../07-bijux-canon-maintain/bijux-canon-dev/sbom-and-supply-chain.md),
and [Compatibility Validation](../../08-compat-packages/migration/validation-strategy.md)
for the governing contracts behind this runbook.
