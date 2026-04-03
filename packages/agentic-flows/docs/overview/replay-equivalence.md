# Replay Equivalence
> Definition of replay equivalence boundaries.

## Bitwise equivalence
Bitwise equivalence means identical persisted artifacts and events at the byte level. It requires the same ordering, timestamps, and serialized payloads. Any single-byte difference is a replay failure. This is the strictest check and is rarely achievable outside controlled runs.

## Semantic equivalence
Semantic equivalence means the same declared contracts and outcomes hold, even if incidental bytes differ. It focuses on plan hashes, dataset identity, and verification outcomes. When semantic equivalence holds, replay remains acceptable for audit. It is the baseline for production acceptability when strict replay is not possible.

## Acceptable divergence
Acceptable divergence is a bounded deviation explicitly allowed by the replay acceptability policy. It requires that deviations are recorded and stay within declared thresholds. Divergence outside those bounds is always a replay rejection. Acceptable divergence does not expand over time or across versions.
