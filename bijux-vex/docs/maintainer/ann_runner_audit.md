# ANN Runner Audit (reference implementation)

Scope: `ReferenceAnnRunner` (`src/bijux_vex/infra/adapters/ann_reference.py`).

## Randomness sources
- `hnswlib` index construction and search order (library-level nondeterminism).
- Seed usage is fixed (`set_seed(0)`), but does not guarantee determinism across platforms.
- Candidate truncation path uses deterministic ordering but is still labeled ANN.

## Non-reproducible steps
- Index build depends on vector insertion order and library behavior.
- HNSW graph structure may vary across builds even with a fixed seed.
- If index persistence is enabled, replay depends on external index file state.

## Audit gaps (to close before ANN graduation)
- No explicit provenance for index build parameters beyond `M` and `ef_search`.
- No checksum/fingerprint for index file contents.
- No capture of library version or hardware characteristics.
- No explicit declaration of whether the truncation fallback was used.

## Notes
- The runner labels `randomness_sources = ("reference_ann_hnsw",)`.
- ANN remains experimental until the gaps above are addressed (see `docs/spec/ann_graduation_criteria.md`).
