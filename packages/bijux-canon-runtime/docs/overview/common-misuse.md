# Common Misuse
> Frequent incorrect assumptions that break guarantees.

- Users assume runs can be replayed without the original dataset; that is wrong because dataset identity is part of the contract; bypassing it breaks replay acceptance.
- Users assume nondeterministic tools are acceptable without explicit authorization; that is wrong because entropy must be declared; ignoring it breaks determinism guarantees.
- Users assume partial traces can be treated as completed runs; that is wrong because finalization is required; skipping it breaks audit integrity.
- Users assume CLI output is a stable API; that is wrong because only contracts are stable; relying on output breaks compatibility expectations.
- Users assume environment changes are harmless; that is wrong because fingerprints must match; drifting environments break replay validation.
