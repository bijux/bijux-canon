
STATUS: AUTHORITATIVE
## Read This Before Filing an Issue

We will close issues immediately if:
- You did not run `make all` and attach logs.
- You request features that relax invariants (e.g., best-effort verification, legacy markers).
- You ask for non-deterministic behavior without recorded artifacts.

Required evidence for valid issues:
- Command(s) run + full logs.
- Trace/plan schema versions and fingerprints.
- Description of whether artifacts under `artifacts/runs/<run_id>/` are intact.

Check first:
- Docs in `docs/start_here.md` and `docs/doc_invariants.md`.
- Existing failure modes in `docs/SECURITY_FAILURE_MODES.md` and `docs/examples/invalid_traces.md`.

If you disagree with the constraints, this is not the right project.***
