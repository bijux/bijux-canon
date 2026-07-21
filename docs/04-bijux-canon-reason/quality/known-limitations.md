---
title: Known Limitations
audience: mixed
type: reference
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-07-21
---

# Known Limitations

Verification establishes that an artifact satisfies declared structural,
provenance, and grounding rules. It does not establish that a real-world claim
is true, complete, current, or appropriate for a consequential decision.

## Epistemic limits

- A valid support span proves that recorded bytes support the trace's linkage;
  it does not prove the source is accurate or authoritative.
- Confidence is an explicit claim field, not a calibrated probability supplied
  automatically by the verifier.
- Hashes detect changed content but cannot detect a faithfully hashed falsehood.
- The verifier checks declared support relationships. It cannot discover all
  omitted counterevidence or unstated assumptions.
- An `insufficient_evidence` outcome is a controlled refusal, not evidence that
  no answer exists.

Human or domain-specific review remains necessary wherever source selection,
interpretation, uncertainty, or consequences exceed the declared checks.

## Reference backend limits

The bundled reasoner is extractive and the local retrieval path uses BM25 over
checked-in or caller-provided corpus material. These components provide a
deterministic reference path, not a claim of state-of-the-art retrieval or
general reasoning. Chunk sizing, overlap, tokenization, corpus composition,
and BM25 parameters materially affect available evidence.

Corpus byte limits constrain input size, but the package is not a distributed
search service. Very large, frequently changing, or remote corpora belong
behind a retrieval integration with its own availability and provenance
contract.

## Replay limits

Replay is deliberately frozen: recorded tool results are reused instead of
calling external tools again. It proves that the recorded inputs and results
produce the same governed trace. It does not prove that an external source
would return the same content now.

Retrieval replay refuses tampered local corpus, index, or provenance artifacts.
An external URI alone is not re-fetched and re-attested. Archive source
material with the run when future verification depends on its exact bytes.

## Evaluation and interface limits

- Evaluation workflow code and metrics artifacts are implemented, but the CLI
  `--suite` help still describes named suites as a placeholder surface. Treat
  suite discovery and packaged suite names as provisional until that public
  contract is finalized.
- Metrics aggregate the cases supplied to a suite. They do not generalize
  beyond the corpus, prompts, constraints, and expected outcomes represented
  there.
- API and CLI size guards protect declared request and artifact reads; they are
  not substitutes for deployment-level quotas, authentication, isolation, or
  malware/content screening.

## Resource limits

Optional run disk, wall-time, and CPU budgets are process-level guardrails
applied by the artifact workflow. They are not a scheduler, sandbox, or hard
real-time guarantee. A tool may consume remote resources beyond what local
measurements capture. Hosting systems must enforce their own process,
filesystem, network, and credential boundaries.
