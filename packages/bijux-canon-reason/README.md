# bijux-canon-reason

<!-- bijux-canon-badges:generated:start -->
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://pypi.org/project/bijux-canon-reason/)
[![Typing: typed](https://img.shields.io/badge/typing-typed%20(PEP%20561)-0A7BBB)](https://pypi.org/project/bijux-canon-reason/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-0F766E)](https://github.com/bijux/bijux-canon/blob/main/LICENSE)
[![CI Status](https://github.com/bijux/bijux-canon/actions/workflows/verify.yml/badge.svg?branch=main)](https://github.com/bijux/bijux-canon/actions/workflows/verify.yml?query=branch%3Amain)
[![GitHub Repository](https://img.shields.io/badge/github-bijux%2Fbijux--canon-181717?logo=github)](https://github.com/bijux/bijux-canon)

[![bijux-canon-reason](https://img.shields.io/pypi/v/bijux-canon-reason?label=reason&logo=pypi)](https://pypi.org/project/bijux-canon-reason/)
[![bijux-canon-runtime](https://img.shields.io/pypi/v/bijux-canon-runtime?label=runtime&logo=pypi)](https://pypi.org/project/bijux-canon-runtime/)
[![bijux-canon](https://img.shields.io/pypi/v/bijux-canon?label=bijux--canon&logo=pypi)](https://pypi.org/project/bijux-canon/)
[![bijux-canon-agent](https://img.shields.io/pypi/v/bijux-canon-agent?label=agent&logo=pypi)](https://pypi.org/project/bijux-canon-agent/)
[![bijux-canon-ingest](https://img.shields.io/pypi/v/bijux-canon-ingest?label=ingest&logo=pypi)](https://pypi.org/project/bijux-canon-ingest/)
[![bijux-canon-index](https://img.shields.io/pypi/v/bijux-canon-index?label=index&logo=pypi)](https://pypi.org/project/bijux-canon-index/)
[![agentic-flows](https://img.shields.io/pypi/v/agentic-flows?label=agentic--flows&logo=pypi)](https://pypi.org/project/agentic-flows/)
[![bijux-agent](https://img.shields.io/pypi/v/bijux-agent?label=bijux--agent&logo=pypi)](https://pypi.org/project/bijux-agent/)
[![bijux-rag](https://img.shields.io/pypi/v/bijux-rag?label=bijux--rag&logo=pypi)](https://pypi.org/project/bijux-rag/)
[![bijux-rar](https://img.shields.io/pypi/v/bijux-rar?label=bijux--rar&logo=pypi)](https://pypi.org/project/bijux-rar/)
[![bijux-vex](https://img.shields.io/pypi/v/bijux-vex?label=bijux--vex&logo=pypi)](https://pypi.org/project/bijux-vex/)

[![bijux-canon-reason](https://img.shields.io/badge/reason-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-reason)
[![bijux-canon-runtime](https://img.shields.io/badge/runtime-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-runtime)
[![bijux-canon](https://img.shields.io/badge/bijux--canon-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon)
[![bijux-canon-agent](https://img.shields.io/badge/agent-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-agent)
[![bijux-canon-ingest](https://img.shields.io/badge/ingest-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-ingest)
[![bijux-canon-index](https://img.shields.io/badge/index-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-index)
[![agentic-flows](https://img.shields.io/badge/agentic--flows-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fagentic-flows)
[![bijux-agent](https://img.shields.io/badge/bijux--agent-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-agent)
[![bijux-rag](https://img.shields.io/badge/bijux--rag-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-rag)
[![bijux-rar](https://img.shields.io/badge/bijux--rar-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-rar)
[![bijux-vex](https://img.shields.io/badge/bijux--vex-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-vex)

[![bijux-canon-reason docs](https://img.shields.io/badge/docs-reason-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/04-bijux-canon-reason/)
[![bijux-canon-runtime docs](https://img.shields.io/badge/docs-runtime-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/06-bijux-canon-runtime/)
[![bijux-canon-agent docs](https://img.shields.io/badge/docs-agent-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/05-bijux-canon-agent/)
[![bijux-canon-ingest docs](https://img.shields.io/badge/docs-ingest-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/02-bijux-canon-ingest/)
[![bijux-canon-index docs](https://img.shields.io/badge/docs-index-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/03-bijux-canon-index/)
<!-- bijux-canon-badges:generated:end -->

`bijux-canon-reason` is the package that turns available evidence into planned
reasoning steps, structured claims, and verification outcomes. It is where
reasoning behavior is made explicit enough to inspect, test, and defend.

If you need to understand how claims are formed, how reasoning steps are
planned and executed, how evidence is used, or where verification lives, start
here. If you need runtime governance, storage, or vector execution internals,
you are outside this package's boundary.

## Reasoning Record

```mermaid
flowchart LR
    problem["ProblemSpec"] --> plan["Plan"]
    plan --> steps["StepOutput + ToolCall"]
    steps --> claims["Claim + SupportRef"]
    claims --> trace["Trace"]
    trace --> report["VerificationReport"]
    report --> replay["fingerprint replay"]
```

The package root exports the stable model and validation vocabulary:
`ProblemSpec`, `Plan`, `PlanNode`, `Claim`, `EvidenceRef`, `SupportRef`,
`ToolRequest`, `ToolResult`, `Trace`, `VerificationCheck`, and
`VerificationReport`, together with canonical serialization, fingerprinting,
stable-ID, and validation helpers.

Support is content-addressed. A `SupportRef` records whether it refers to a
claim, evidence item, or tool call; its source identity; an exact non-empty
span; and the SHA-256 digest of the cited snippet. Claims separately record
their observed, assumed, or derived type and proposed, validated, or rejected
status.

## CLI Workflow

```bash
bijux-canon-reason run \
  --spec problem.json \
  --preset default \
  --seed 0 \
  --artifacts-dir artifacts/bijux-canon-reason \
  --fail-on-verify \
  --json

bijux-canon-reason verify \
  --trace artifacts/bijux-canon-reason/runs/<run-id>/trace.jsonl \
  --plan artifacts/bijux-canon-reason/runs/<run-id>/plan.json \
  --fail-on-verify --json

bijux-canon-reason replay \
  --trace artifacts/bijux-canon-reason/runs/<run-id>/trace.jsonl \
  --fail-on-diff --json
```

`run` writes `spec.json`, `plan.json`, `trace.jsonl`, `verify.json`,
`fingerprint.txt`, `run_meta.json`, and `manifest.json` beneath a stable run
identifier. The manifest and invariant checksum bind the inputs, plan, trace,
runtime descriptor, schema version, and producer version.

The `eval` command exists, but its suite selector is currently a fixed stub. It
must not be treated as evidence of a mature configurable evaluation catalog.

## HTTP Contract

The v1 API supports health, item CRUD, run creation, run lookup, manifest and
trace retrieval, verification, and replay. Its source, pinned representation,
and digest live under
[`apis/bijux-canon-reason/v1/`](../../apis/bijux-canon-reason/v1/).

## Evaluate A Reasoning Claim

| Question | Evidence to inspect | What is not enough |
| --- | --- | --- |
| Where did the claim originate? | claim kind, introducing event, plan node, stable identity | final prose alone |
| Which bytes support it? | evidence identity, exact span, snippet digest, `SupportRef` | a source title or confidence score |
| Was it validated or rejected? | verification checks, findings, claim status, policy disposition | trace completion alone |
| Is the run complete? | manifest, file digests, invariant checksum, producer and schema versions | presence of a run directory |
| Did replay match? | original and replay fingerprints plus diff summary | similar-looking output |

Verification proves that registered checks passed over retained evidence. It
does not prove corpus completeness, scientific truth, or correctness of an
unstated inference.

## Package Continuity

[`bijux-rar`](https://pypi.org/project/bijux-rar/) is an exact-version
compatibility distribution for this package. It preserves the `bijux_rar`
import root and delegates to canonical reasoning modules. The
`bijux-canon-reason` distribution currently registers both the
`bijux-canon-reason` and `bijux-rar` commands against the same canonical
application; command continuity does not make the old Python root canonical.

Use `bijux_canon_reason` and `bijux-canon-reason` in new integrations. Follow
the [migration guide](https://bijux.io/bijux-canon/08-compat-packages/migration/migration-guidance/)
to validate plans, claims, traces, provenance, and stored-artifact readers. The
former [`bijux/bijux-rar`](https://github.com/bijux/bijux-rar) repository is
historical; current implementation authority is this repository.

## Package Boundary

Reason owns content-addressed planning, local tool execution, evidence-linked
claims, reasoning traces, and reasoning-level verification. It consumes
prepared and retrieved evidence without taking ownership of source
normalization or vector ranking. Agent may coordinate several reasoning calls;
runtime decides whether the resulting whole run is acceptable and durable.

Downstream consumers should preserve the run manifest and exact support
references. Rebuilding a citation from display text loses the byte-level
contract that verification and replay depend on.

## Verification And Failure Semantics

- trace and plan validation reject invalid topology and inconsistent event
  structure before successful verification
- evidence paths are constrained and provenance references are checked rather
  than trusted as arbitrary filesystem input
- `--fail-on-verify` promotes verification findings to exit status `2` while
  retaining the machine-readable report
- replay compares original and reproduced trace fingerprints and returns a diff
  summary on mismatch
- disk, wall-time, CPU, corpus-size, and retrieval limits are explicit runtime
  controls, not undocumented environment behavior

## Source Map

- [`src/bijux_canon_reason/planning`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-reason/src/bijux_canon_reason/planning) for planning behavior
- [`src/bijux_canon_reason/reasoning`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-reason/src/bijux_canon_reason/reasoning) for claim and reasoning semantics
- [`src/bijux_canon_reason/execution`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-reason/src/bijux_canon_reason/execution) for step execution
- [`src/bijux_canon_reason/verification`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-reason/src/bijux_canon_reason/verification) for checks and outcomes
- [`src/bijux_canon_reason/interfaces`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-reason/src/bijux_canon_reason/interfaces) and [`src/bijux_canon_reason/api`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-reason/src/bijux_canon_reason/api) for boundaries
- [`tests`](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-reason/tests) for executable protection of the package contract

## Read This Next

- [Package guide](https://bijux.io/bijux-canon/04-bijux-canon-reason/)
- [Ownership boundary](https://bijux.io/bijux-canon/04-bijux-canon-reason/foundation/ownership-boundary/)
- [Architecture overview](https://bijux.io/bijux-canon/04-bijux-canon-reason/architecture/)
- [Interface contracts](https://bijux.io/bijux-canon/04-bijux-canon-reason/interfaces/)
- [Compatibility packages](https://bijux.io/bijux-canon/08-compat-packages/)
- [Test strategy](https://bijux.io/bijux-canon/04-bijux-canon-reason/quality/test-strategy/)
- [Changelog](https://github.com/bijux/bijux-canon/blob/main/packages/bijux-canon-reason/CHANGELOG.md)

## Primary Entrypoint

- console script: `bijux-canon-reason`
- package history: [`CHANGELOG.md`](CHANGELOG.md)
