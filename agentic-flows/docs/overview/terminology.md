# Terminology
> Binding vocabulary for this system.

Flow: A declared, versioned plan for how a run should execute.
Run: One execution attempt of a flow with a fixed configuration and recorded trace.
Replay: Re-execution of a run using persisted inputs and envelopes to compare outcomes.
Determinism: The degree to which replays should produce identical traces and artifacts.
Acceptability: The policy threshold for deciding whether a replay divergence is allowed.
Entropy: Any non-deterministic influence that must be declared and audited.
