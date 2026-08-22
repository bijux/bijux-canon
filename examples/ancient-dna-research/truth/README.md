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
qrels, claims, citation relations, conflicts, abstention labels, and evaluation
splits remain separately governed truth.
