# Ancient-DNA research locator truth

`locator-truth.jsonl` records independently reviewed exact passages from every
locked article in the research corpus. Each source has a title, abstract
paragraph, body section heading, and body paragraph bound to its immutable
source digest, JATS element path, normalized character span, exact text hash,
review date, and corpus-lock identity.

Validate the set against the tracked source bytes with:

```console
python -m bijux_canon_dev.corpus.research_locator_truth \
  --lock examples/ancient-dna-research/corpus.lock.json \
  --research-root examples/ancient-dna-research \
  --truth examples/ancient-dna-research/truth/locator-truth.jsonl
```

These records establish source resolution and exact-text integrity. Scientific
claims, citation relations, conflicts, abstention labels, and evaluation splits
remain separately governed truth.

`qrels.jsonl` contains source-first retrieval judgments for one substantive
research question per locked article. Each judgment has a relevance grade,
rationale, primary adjudicator identity, complete canonical ingest chunk
manifest and mapping identities, and one or more exact locator-truth anchors.
The labels were reviewed from source content before retrieval evaluation;
system rankings are explicitly forbidden as label input.

Validate the qrels and their embedded chunk identities with:

```console
python -m bijux_canon_dev.corpus.research_qrels \
  --lock examples/ancient-dna-research/corpus.lock.json \
  --research-root examples/ancient-dna-research \
  --locator-truth examples/ancient-dna-research/truth/locator-truth.jsonl \
  --qrels examples/ancient-dna-research/truth/qrels.jsonl
```

`claim-truth.jsonl` defines one atomic expected, optional, opposed, and
forbidden claim for every locked article. Supported claims bind to exact
supporting spans; opposed and forbidden claims bind to exact opposing or
limiting spans and require abstention. Every citation resolves through a
validated qrel chunk rather than a detached text copy.

Validate claim classes, abstention policy, and exact citation spans with:

```console
python -m bijux_canon_dev.corpus.research_claim_truth \
  --lock examples/ancient-dna-research/corpus.lock.json \
  --research-root examples/ancient-dna-research \
  --locator-truth examples/ancient-dna-research/truth/locator-truth.jsonl \
  --qrels examples/ancient-dna-research/truth/qrels.jsonl \
  --claim-truth examples/ancient-dna-research/truth/claim-truth.jsonl
```

`split.json` freezes the complete same-source cross-product of 30 graded qrel
judgments and four atomic claim classes into exactly 120 reviewed evaluation
cases. The partition contains 80 development and 40 held-out cases, balances
ten held-out cases per claim class, records query/evidence/conflict/negative/
format/difficulty strata, prohibits tuning use of held-out labels, and hashes
every case and the complete split.

`evaluation-cases.jsonl` is the canonical line-oriented execution inventory for
those 120 cases. Every row joins the frozen split to its reviewed question,
single-source corpus scope, source filter, answerability decision, and combined
retrieval/claim rationale without consulting system output. It is regenerated
from the validated split, qrels, and claim truth with `--cases-output`; byte
drift fails the repository test suite.

Validate the frozen case construction, strata, partition isolation, and hashes
with:

```console
python -m bijux_canon_dev.corpus.research_evaluation_split \
  --lock examples/ancient-dna-research/corpus.lock.json \
  --research-root examples/ancient-dna-research \
  --locator-truth examples/ancient-dna-research/truth/locator-truth.jsonl \
  --qrels examples/ancient-dna-research/truth/qrels.jsonl \
  --claim-truth examples/ancient-dna-research/truth/claim-truth.jsonl \
  --split examples/ancient-dna-research/truth/split.json \
  --cases-output examples/ancient-dna-research/truth/evaluation-cases.jsonl
```
