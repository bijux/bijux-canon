# Testing (maintainer)

The test suite exists to prevent contract drift.

## What tests must cover

- documentation checksum invariant
- trace schema validation and upgrade paths
- failure taxonomy completeness and validation
- CLI/API surfaces producing coherent artifacts

## Running tests

```bash
make test
```

If you are iterating quickly:

```bash
pytest -q
```

## Invariant tests

Invariant tests are allowed to be strict. If an invariant test fails, do not “fix” it by weakening the invariant without updating the spec and versioning appropriately.
