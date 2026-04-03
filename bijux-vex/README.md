# bijux-vex — explicit vector execution

[![PyPI - Version](https://img.shields.io/pypi/v/bijux-vex.svg)](https://pypi.org/project/bijux-vex/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![Typing: typed (PEP 561)](https://img.shields.io/badge/typing-typed-4F8CC9.svg)](https://peps.python.org/pep-0561/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/bijux/bijux-vex/raw/main/LICENSES/MIT.txt)
[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-brightgreen)](https://bijux.github.io/bijux-vex/)
[![CI Status](https://github.com/bijux/bijux-vex/actions/workflows/ci.yml/badge.svg)](https://github.com/bijux/bijux-vex/actions)

**What it is**  
Bijux‑Vex is a vector execution runtime with replayable determinism and audited ND (ANN).

**Why it exists**  
Production vector search drifts quietly. Bijux‑Vex makes correctness explicit and refuses when guarantees cannot be met.

**Anti‑goals**  
Not a vector DB. Not a RAG framework. Not a hosted service. No implicit “best‑effort” correctness.

## Quickstart (deterministic)

```bash
python -m bijux_vex.boundaries.cli.app ingest --doc "hello" --vector "[0,1,0]" --vector-store memory
python -m bijux_vex.boundaries.cli.app materialize --execution-contract deterministic --vector-store memory
python -m bijux_vex.boundaries.cli.app execute --vector "[0,1,0]" \
  --execution-contract deterministic \
  --execution-intent exact_validation \
  --vector-store memory
```

## Start Here

- Start here (10 minutes): https://bijux.github.io/bijux-vex/user/start_here_10_minutes/
- Start here (human): https://bijux.github.io/bijux-vex/user/start_here_human/
- Start here (canonical doc): `docs/user/start_here.md`
- Why Bijux‑Vex exists: https://bijux.github.io/bijux-vex/user/why_bijux_vex_exists/
- Docs home: https://bijux.github.io/bijux-vex/

## Production readiness (explicit)

- Determinism enforced and replayable
- ND is bounded and audited
- CI gates required before release

## Project values

- Correctness over convenience
- Explicit over implicit
- Honest failure over silent success
