# Evaluation evidence books

Evaluation evidence books are generated run products, not source-controlled truth.
The durable implementation is
`bijux_canon_dev.quality.EvaluationEvidenceBookGenerator`; generated files may be
written under the repository `artifacts/` directory and deleted after review.

The generator accepts only a source commit equal to the current commit. Each book
retains per-case metrics, errors and exclusions; aggregate numerators,
denominators, confidence intervals and baselines; source, data, model and
configuration identities; limitations; and exact reproduction commands.

Regeneration writes a canonical JSON index, one JSON record per case, and a
GitHub-renderable Markdown summary. Identical inputs produce byte-identical
outputs, so no evaluation logic or unique evidence is lost when generated output
is disposed.
