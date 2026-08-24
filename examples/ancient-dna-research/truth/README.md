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

`question-partition-review.jsonl` records the reviewed evidence-family decision
for every semantic question. `split.json` freezes exactly one case per question:
12 development questions in three complete families and six held-out questions
in the complete resin-preservation family. No question or evidence family
crosses partitions. The split binds the exact question, qrel, partition-review,
development-label, held-out-label, case-set, corpus-lock, and split identities.

The eight original single-source qrel queries, 30 qrels, and 32 atomic claims
remain useful truth inventories, but they are no longer multiplied into fake
execution cases. Metrics use the 18 unique semantic question IDs as their
denominator. Each question's evidence edge carries a relevance grade reviewed
for that exact question; a grade from the old single-source query is not reused
as if it answered a different query.

`evaluation-cases.jsonl` is the canonical runnable inventory. Its 12
development rows expose reviewed answer points, abstention outcomes, and exact
evidence. Its six held-out rows expose only the prompt, case identity, family,
and label-set hash. Held-out answer points, evidence IDs, relations, and grades
are absent. The release evaluator is the sole executable interface that joins
a complete held-out submission to sealed labels, and it returns aggregates
rather than the labels.

`question-claim-truth.jsonl` makes the 31 visible development answer points
executable without deriving truth from a system answer. It binds every point to
its exact reviewed qrels and support, opposition, limitation, or insufficiency
relation. Twenty-five points are expected answer claims; six are grounded
abstention reasons. The crosswalk was reviewed source-first without consulting
system output. It does not expose or reconstruct held-out labels.

Publication metadata is an integrity prerequisite, not research evidence.
Checks for eight titles, DOIs, authors, journals, licenses, and provenance prove
that ingest retained bibliographic truth; they do not prove retrieval or RAG.
The primary product evidence is execution of the semantic questions against
the installed persistent index. Each run must retrieve source content, retain
exact chunk-to-document locators, and report every reviewed judgment in the
denominator. The resulting stage analysis distinguishes raw candidate reach,
fusion loss, content-aware reranking, and final top-five recall.

RAG and RAR evaluation must consume these content-bearing chunks. Useful
evidence includes atomic findings, methods, limitations, conflicts,
cross-paper synthesis, and correct abstention. A list of bibliographic fields,
the presence of a citation, or lexical overlap alone is never counted as an
answered research question.

Question and partition amendments require a source-first reviewer identity,
date, method, and rationale different from the primary qrel/claim adjudicator.
System output may not select questions, families, splits, answer points,
evidence, or relevance grades. Any accepted amendment regenerates and reviews
all bound hashes. The older qrels and atomic claims still need another reviewer,
so the audit retains that release blocker without weakening the independently
reviewed question partition.

Validate the frozen case construction, strata, partition indexes, and hashes
with:

```console
python -m bijux_canon_dev.corpus.research_evaluation_split \
  --lock examples/ancient-dna-research/corpus.lock.json \
  --research-root examples/ancient-dna-research \
  --locator-truth examples/ancient-dna-research/truth/locator-truth.jsonl \
  --partition-review examples/ancient-dna-research/truth/question-partition-review.jsonl \
  --qrels examples/ancient-dna-research/truth/qrels.jsonl \
  --questions examples/ancient-dna-research/truth/research-questions.jsonl \
  --split examples/ancient-dna-research/truth/split.json \
  --cases-output examples/ancient-dna-research/truth/evaluation-cases.jsonl
```

Release-only retrieval scoring requires a canonical submission containing every
held-out `question_id` and its ordered `retrieved_qrel_ids`. The operator must
set `BIJUX_CANON_RELEASE_EVALUATION` to the exact frozen split identity. The
command refuses missing, duplicate, extra, or unauthorized populations:

```console
python -m bijux_canon_dev.corpus.research_release_evaluation \
  --lock examples/ancient-dna-research/corpus.lock.json \
  --research-root examples/ancient-dna-research \
  --locator-truth examples/ancient-dna-research/truth/locator-truth.jsonl \
  --partition-review examples/ancient-dna-research/truth/question-partition-review.jsonl \
  --qrels examples/ancient-dna-research/truth/qrels.jsonl \
  --questions examples/ancient-dna-research/truth/research-questions.jsonl \
  --split examples/ancient-dna-research/truth/split.json \
  --submission /path/to/canonical-heldout-ranking.jsonl
```

Audit semantic denominators, duplicates, contradictions, reviewer provenance,
label sealing, and development/held-out family overlap with:

```console
python -m bijux_canon_dev.corpus.research_truth_audit \
  --qrels examples/ancient-dna-research/truth/qrels.jsonl \
  --questions examples/ancient-dna-research/truth/research-questions.jsonl \
  --question-claim-truth examples/ancient-dna-research/truth/question-claim-truth.jsonl \
  --claim-truth examples/ancient-dna-research/truth/claim-truth.jsonl \
  --split examples/ancient-dna-research/truth/split.json \
  --cases examples/ancient-dna-research/truth/evaluation-cases.jsonl
```
