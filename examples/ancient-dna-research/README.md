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

## CPU exact and ANN hybrid workflow

The sibling `cpu_hybrid_workflow.py` exercises the installed `local-cpu`
profile with the pinned `sentence-transformers/all-MiniLM-L6-v2` revision. It
validates the retained model files and license metadata with a real bounded CPU
inference, ingests the eight JATS sources, and persists one generation with
SQLite FTS5, FAISS exact, and FAISS HNSW segments. After switching from a
relative to an absolute workspace spelling, separate Runtime processes execute
both exact and ANN hybrid searches. The runner rejects fallback and requires
the returned evidence to retain both lexical and selected dense-channel
contributions.

Acquire the model while network access is permitted, then run the workflow
with network disabled:

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

The workflow uses only the visible development split. It executes all 12
questions and 29 reviewed qrels from persisted system results and fails below
Recall@5 `0.90`, MRR@10 `0.85`, or nDCG@10 `0.85`. It never opens sealed
held-out labels. It also executes the development
`adna-multihop-contamination-strategy` case through bounded research and rejects
the run unless it retains the initial answer, pursues distinct evidence needs,
classifies candidates, makes a warranted cited revision, and stops under an
inspectable iteration/tool/result/time/token policy. `summary.json` retains the
model revision, license, file-set digest, 384-dimensional model lock, segment
backends, corpus/index/configuration identities, exact and ANN run/attempt
identities, ordered-evidence reproducibility, evaluation arithmetic, and the
research trace and terminal identities.

On macOS, run the installed acceptance test with OS-level network denial:

```bash
BIJUX_CANON_RUNTIME_INSTALLED_COMMAND="$PWD/artifacts/ancient-dna-cpu/venv/bin/bijux-canon-runtime" \
BIJUX_CANON_INDEX_INSTALLED_COMMAND="$PWD/artifacts/ancient-dna-cpu/venv/bin/bijux-canon-index" \
BIJUX_CANON_INSTALLED_MODEL_DIRECTORY="$PWD/artifacts/ancient-dna-cpu/models/local-minilm-384/1110a243fdf4706b3f48f1d95db1a4f5529b4d41" \
  artifacts/root/check-venv/bin/python -m pytest -q -c configs/pytest.ini \
    -p no:cacheprovider -o addopts= \
    packages/bijux-canon-runtime/tests/e2e/test_installed_cpu_hybrid_workflow.py
```
