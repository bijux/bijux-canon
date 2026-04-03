# Glossary

determinism
A property where the same inputs produce the same outputs under the same system and index state.

non-determinism (ND)
Execution that allows approximation or randomness and must declare its bounds and randomness profile.

replay
A verification process that re-executes under the same contract and compares results to a prior run.

provenance
A structured record of inputs, decisions, randomness, and artifacts emitted by an execution.

execution artifact
A persisted representation of the execution state and index configuration used for later runs.

witness
An optional verification step for ND that estimates quality by checking against exact results on a subset.

approximation
A deliberate tradeoff where results may differ from exact in exchange for speed or scale.

confidence label
A classification derived from ND quality metrics that indicates result stability.

refusal
A structured response indicating the system will not execute because guarantees cannot be met.
