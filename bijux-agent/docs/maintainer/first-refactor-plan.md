# First refactor plan (maintainer)

A pragmatic first refactor should reduce risk, not expand scope.

## Proposed first steps

1. **Lock trace schema discipline**
   - ensure every run writes a valid trace (normal run)
   - validate/upgrade trace payloads consistently

2. **Align CLI and API**
   - same minimal artifact semantics for equivalent inputs/config
   - consistent error mapping and termination reasons

3. **Simplify configuration**
   - make “what config keys matter” obvious
   - keep defaults in one place

4. **Strengthen tests**
   - add small fixtures that validate trace headers and failure taxonomy

If you cannot explain the refactor in one page, it’s probably too big.
