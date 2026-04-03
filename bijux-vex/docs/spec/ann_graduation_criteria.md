# ANN Graduation Criteria (experimental → stable)

ANN remains **experimental** until all criteria below are met and recorded.

## Criteria
- **Determinism envelope**: replay divergence stays within declared bounds across repeated runs.
- **Audit completeness**: approximation reports include algorithm/version, params, and randomness sources.
- **Budget compliance**: ANN budget enforcement is deterministic and test-covered.
- **Cross-backend consistency**: at least one cross-backend replay/compare test passes for ANN.
- **Performance baseline**: benchmark harness exists and regressions are measurable.
- **Failure semantics**: ANN failures produce explicit errors; no silent fallback.

## Graduation checklist
- All criteria above satisfied and documented.
- ANN status flipped to `stable` in capabilities output.
- Documentation updated to remove “experimental” labels.

Until then, ANN output must be labeled **experimental** in CLI/API/provenance.
