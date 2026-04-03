# Determinism Rules

These rules define the determinism gate. Identical inputs + configuration must yield byte-identical artifacts.
They apply to the deterministic execution contract only; ANN mode is documented separately in `execution_contracts.md` and explicitly forfeits replayability.

## Canonical JSON
- Serialize with sorted keys.
- Lists must be emitted in a stable order; upstream ordering must be deterministic before serialization.
- No implicit defaults: every serialized field is explicit and ordered.
- Encoding is UTF-8 without BOM; no trailing whitespace.

## Float Normalization
- NaN and ±Inf are forbidden; validation must reject them.
- Finite floats are normalized via canonical JSON string form produced by Python `repr` on `float` (deterministic across runs for finite values).
- No rounding/quantization beyond the source value; callers must pre-quantize if needed.

## Ranking Tie-Breaks
- Ranking order is `(score, vector_id, chunk_id, document_id)` ascending by score, then lexicographic by IDs.
- Scores that compare equal after normalization must still be ordered by these explicit keys.
- Backends must not introduce hidden randomness; any deterministic seed must be part of the query spec.

## Example (executable)
>>> from bijux_vex.core.identity.ids import fingerprint
>>> fp1 = fingerprint({"doc": 1})
>>> fp2 = fingerprint({"doc": 1})
>>> fp1 == fp2
True
