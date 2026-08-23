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

`research-questions.jsonl` is the content-first semantic question authority.
It contains 18 independently source-reviewed questions: two each for findings,
methods, population/context, limitations, conflicts, cross-paper synthesis,
multi-hop reasoning, ambiguity, and out-of-scope abstention. Each record names
acceptable answer points, an answerability and abstention disposition, exact
reachable qrel evidence with support/opposition/limitation/context relations,
and secondary reviewer provenance. Product output may neither define nor amend
this truth.

Validate question diversity, exact evidence reachability, category balance,
paraphrase exclusion, and review independence with:

```console
python -m bijux_canon_dev.corpus.research_questions \
  --qrels examples/ancient-dna-research/truth/qrels.jsonl \
  --questions examples/ancient-dna-research/truth/research-questions.jsonl
```

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

`split.json` freezes the legacy same-source cross-product of 30 graded qrel
judgments and 32 atomic claims into exactly 120 reviewed execution rows. Those
rows are not 120 independent questions or claims. The semantic populations are
18 reviewed semantic questions, 8 legacy single-source qrel queries, 30 qrels,
32 atomic claims, and 120 unique legacy qrel/claim pairs. Metrics must declare
which population they aggregate and use that population's unique identities as
their denominator.

The current row partition contains 80 development and 40 held-out rows and
prohibits tuning use of held-out labels. It is not leakage-resistant: all 8
query identities, 27 of 30 qrel identities, and all 32 claim identities occur
in both partitions. A release-eligible held-out corpus must replace this split
with disjoint reviewed semantic identities. Until then, these rows support
development diagnostics but cannot prove held-out generalization.
The 18 semantic questions intentionally do not enter this obsolete cross-product;
they become the question-level authority for the leakage-resistant replacement.

`evaluation-cases.jsonl` is the canonical line-oriented execution inventory for
those 120 cases. Every row joins the frozen split to its reviewed question,
single-source corpus scope, source filter, answerability decision, and combined
retrieval/claim rationale without consulting system output. Applicable cases
embed their graded qrel, exact content-hashed chunk span, and adjudication
lineage. Negative cases retain an explicit empty-qrel disposition rather than
silently disappearing from metric denominators. Each row also embeds its atomic
claim class, exact claim-citation relation and span, conflict expectation, and
abstention outcome. The file is regenerated from the validated split, qrels,
and claim truth with `--cases-output`; byte drift fails the repository test
suite.

The qrels, claims, and split currently record primary manual review by
`bijux-corpus-curation-primary` on 2026-08-22. Qrels use source-first
adjudication before retrieval evaluation; claims use source-first atomic-claim
and citation adjudication. Qrels explicitly record that system rankings were
not consulted; the claim records do not carry an equivalent explicit field.
Independent review is still required for release truth, so the audit marks that
condition for review instead of inferring certainty from product output.

Validate the frozen case construction, strata, partition indexes, and hashes
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

Audit semantic denominators, duplicates, contradictions, reviewer provenance,
source cross-products, and development/held-out overlap with:

```console
python -m bijux_canon_dev.corpus.research_truth_audit \
  --qrels examples/ancient-dna-research/truth/qrels.jsonl \
  --questions examples/ancient-dna-research/truth/research-questions.jsonl \
  --claim-truth examples/ancient-dna-research/truth/claim-truth.jsonl \
  --split examples/ancient-dna-research/truth/split.json \
  --cases examples/ancient-dna-research/truth/evaluation-cases.jsonl
```
