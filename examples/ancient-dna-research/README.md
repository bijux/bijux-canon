# Offline ancient-DNA research workflow

This example proves the base `bijux-canon-runtime` installation as a complete,
secret-free lexical product. It discovers and ingests the eight reviewed JATS
articles in [`corpus/sources`](corpus/sources), builds a durable SQLite FTS5
index, retrieves evidence, produces an admitted grounded answer, resolves every
citation to the retained source digest and JATS element, reopens the workspace,
replays the answer, and compares outcome, claims, and citations.

No embedding model, provider credential, network request, or optional runtime
extra is used. The runner removes `PYTHONPATH` and the embedding-model override
from installed Runtime subprocesses. It also points proxy variables at a closed
loopback port. For release acceptance, run it under an operating-system network
denial as described below.

## Run from an installed wheel

Create a base-only environment, then invoke the example from a fresh directory:

```bash
python -m venv artifacts/ancient-dna-offline/venv
artifacts/ancient-dna-offline/venv/bin/python -m pip install bijux-canon-runtime

python examples/ancient-dna-research/offline_lexical_workflow.py \
  --runtime-command artifacts/ancient-dna-offline/venv/bin/bijux-canon-runtime \
  --workspace artifacts/ancient-dna-offline/runtime-workspace \
  --evidence-directory artifacts/ancient-dna-offline/evidence
```

Both the workspace and evidence directory must be new. The workspace is the
durable product state; retain it to inspect jobs and runs, restart Runtime,
replay work, compare attempts, or create a governed backup. The evidence
directory contains each public CLI exchange, bounded artifact pages, the
assembled checksum-verified claim graph, and `summary.json`.

The runner exits nonzero unless all eight sources are admitted without
rejection, corpus and index chunk counts agree, the index backend is
`sqlite-fts5`, the answer has verified causal provenance, every exact quote
resolves into the named source bytes, the default inspection page is bounded to
five items, absolute-path restart succeeds, and replay preserves exact artifact
identities.

## Release acceptance with network denied

On macOS, the repository acceptance test wraps the copied example in
`sandbox-exec` and denies all network access:

```bash
BIJUX_CANON_RUNTIME_INSTALLED_COMMAND="$PWD/artifacts/ancient-dna-offline/venv/bin/bijux-canon-runtime" \
  artifacts/root/check-venv/bin/python -m pytest -q -p no:cacheprovider \
    -o addopts= \
    packages/bijux-canon-runtime/tests/e2e/test_installed_offline_lexical_workflow.py
```

The acceptance test copies the runner and corpus to pytest's temporary
directory before execution. It also rejects installed `sys.path` entries that
resolve to this repository's package source trees, so an editable checkout
cannot masquerade as wheel evidence. On another operating system, run the same
command inside that platform's network-isolated sandbox; the runner records the
caller-provided `BIJUX_CANON_NETWORK_ISOLATION` description in `summary.json`.

## Inspect the durable result

The compact summary records the job, run, attempt, corpus, index, citation,
replay, comparison, distribution, and workspace identities needed for later
inspection. With the retained workspace:

```bash
export BIJUX_CANON_RUNTIME_WORKING_ROOT="$PWD/artifacts/ancient-dna-offline/runtime-workspace"

bijux-canon-runtime v2 inspect RUN_ID
bijux-canon-runtime v2 artifact-payload CLAIM_GRAPH_ARTIFACT_ID \
  --offset 0 \
  --max-bytes 65536
bijux-canon-runtime v2 compare RUN_ID RUN_ID \
  --baseline-attempt-id INITIAL_ATTEMPT_ID \
  --candidate-attempt-id REPLAY_ATTEMPT_ID \
  --dimension outcome \
  --dimension claims \
  --dimension citations
```

Default inspection returns counts and at most five values from each collection.
Artifact payloads require deliberate paging and never return more than 65,536
decoded bytes per request.

The sibling [`truth`](truth) directory is governed evaluation material. The
workflow does not read it: product output is generated from the corpus alone,
and held-out labels remain outside development execution.
