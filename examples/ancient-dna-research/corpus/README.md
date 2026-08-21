# Ancient-DNA research JATS corpus

This directory contains the exact full-text JATS bytes for the eight reviewed
PLOS articles in the Bijux Canon ancient-DNA research portfolio. The files are
durable example inputs; transient downloads, execution logs, and verification
evidence remain under the ignored repository `artifacts/` tree.

`corpus-manifest.json` binds every source file to its stable source ID, DOI,
acquisition receipt, SHA-256 digest, byte count, article structure, license,
attribution, and supplementary links. The JATS files are copied without
transformation from the immutable acquisition snapshot.

The articles are licensed under the article-specific terms recorded in the
manifest. Supplementary assets are not included and require separate review.
Materialization does not make the corpus truth-annotated, admitted, held out,
or published.

Regenerate the portfolio with the repository-owned
`bijux_canon_dev.corpus.materialization` module after completing source review
and acquisition. The command must use current acquisition receipts and the
live production-finalization graph; it refuses to replace different bytes at a
stable source path.
