# Evaluation evidence books

Evaluation evidence books are generated run products, not source-controlled truth.
The durable implementation is
`bijux_canon_dev.quality.EvaluationEvidenceBookGenerator`; generated files may be
written under the repository `artifacts/` directory and deleted after review.

The generator accepts only a source commit equal to the current commit. Each book
retains per-case metrics, terminal execution status, typed failures, label
completeness, errors and exclusions. Aggregate records retain their metric
definition version, aggregation method, exact case population, semantic
denominator, arithmetic, dispersion, confidence interval, worst cases and
baseline. Source, data, model and configuration identities, limitations and exact
reproduction commands remain part of the book.

An evidence book cannot omit a failed, refused, cancelled or budget-exhausted
case from an aggregate. Every aggregate names exactly the same unique case
population as the book, every retained case has a value for that metric, and the
book always includes `completion.product-success-rate`. This prevents a
conditional seven-of-eight score from being presented as an eight-query product
result.

## Product metric contract

`bijux_canon_reason.evaluation.product_metric_catalog()` is the authoritative,
versioned definition catalog. The unconditional evaluator emits one sample for
every metric and every declared semantic case. A typed non-completion follows the
metric's declared conservative value; it never becomes an exclusion. Warm
latency is the exception: its observed duration remains in the percentile even
when the attempt fails.

The catalog covers the release quality surfaces and their semantic populations:

| Surface | Metrics | Population and failure treatment |
|---|---|---|
| retrieval | Recall@5, reciprocal rank@10, nDCG@10 | unique reviewed questions; refused and failed queries score zero |
| ANN/VEX | exact-witness Recall@10 | unique reviewed dense questions; below-policy refusal scores zero |
| claims | expected-claim recall, supported-claim coverage | independently reviewed expected claims and emitted atomic claims |
| citations | precision and recall | reviewed claim-to-evidence relations; an answered output with no citations receives a zero-valued case charge |
| abstention | correctness | unique reviewed answerability cases; grounded abstention can be a completed correct outcome |
| conflicts | retention and false-consensus rate | independently reviewed conflicts and qualifications |
| RAR | requirement coverage, counterevidence recall, classification completeness, paired expected-claim gain, unsupported-claim rate, completed material closure | identical question, corpus, base retrieval, and retrieval configuration; incomplete research receives conservative values |
| latency | warm hybrid engine and operator p95 | every attempted query, including terminal failures |
| completion | product success rate | every attempted case; refusal, failure, cancellation and budget exhaustion score zero |

Macro means are used only when each unique question is the population unit.
Micro ratios are used for reviewed relations or claims and retain their raw
numerators and denominators. Paired RAG/RAR gain is averaged across identical
question pairs. Each pair binds the content-addressed convergence evidence from
the research trace, including remaining requirements, unresolved
classifications, blocking gaps, unsearched important claims, answer revision,
conflicts, and marginal evidence. Per-case outcomes retain RAG and RAR tool
calls, costs, latency, iterations, and exact convergence reasons; tool volume
never contributes quality credit. Latency uses the deterministic nearest-rank
p95. Every result also reports per-case values, population standard deviation,
an explicit uncertainty method, terminal status counts, partial-label counts and
deterministic worst-case identities.

Claim and citation scoring never matches answer text by exact string or keyword
overlap. Independently authored claim-match reviews bind the exact frozen truth,
system output, and emitted atomic claim, then record semantic equivalence plus
entity, scope, quantity, modality, and negation retention. An overgeneralized,
contradictory, unrelated, or ambiguous claim receives no equivalence credit even
when it has an integrity-valid citation. Multiple reviewer decisions remain in
the content-addressed report; disagreement is unresolved until a distinct
adjudicator binds and resolves the exact review artifacts. Representative
semantic errors remain report data rather than disappearing from aggregates.

The ancient-DNA development adapter consumes the sealed case inventory,
source-first question-claim crosswalk, reviewed qrels, and immutable source URIs.
It exposes 12 development questions, 31 reviewed answer or abstention points,
and 48 exact claim-evidence relations as typed evaluation truth; held-out labels
are not an adapter input. Installed citations use the v2 system-citation record,
which retains the emitted exact quote and retrieval chunk identity. Integrity is
measured from that quote, its hash, the immutable source bytes, and the reviewed
chunk binding instead of requiring a system locator to copy a truth locator.

`budget-exhausted` is an incomplete execution status. It requires a typed failure
code, cannot claim an answer disposition, scores zero in completion, and receives
the declared conservative values for counterevidence, revision and unsupported
claims. A completed grounded abstention remains distinct from both refusal and
failure and is evaluated by abstention correctness.

Publication metadata checks remain integrity evidence only. They prove that the
right papers and provenance entered the corpus; they do not contribute a RAG or
RAR quality numerator. Research quality is measured from actual content questions,
retrieved chunks, atomic claims, exact evidence relations, limitations, conflicts,
abstentions and answer revision.

Regeneration writes a canonical JSON index, one JSON record per case, and a
GitHub-renderable Markdown summary. Identical inputs produce byte-identical
outputs, so no evaluation logic or unique evidence is lost when generated output
is disposed.
