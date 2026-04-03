# Tests

Testing remains package-owned, but the repository defines a few shared rules.

## Shared Rules

- tests run from the owning package directory
- test artifacts belong under `artifacts/`
- shared test policy belongs in `configs/` and `makes/`
- repository changes that affect multiple packages should be validated in every
  affected package

## Typical Package Commands

- `make -C packages/<package> test`
- `make -C packages/<package> lint`
- `make -C packages/<package> quality`

Use the smallest relevant verification set while developing, then run the full
set for the packages touched by the change.
