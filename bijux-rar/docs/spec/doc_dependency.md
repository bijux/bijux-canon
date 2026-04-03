STATUS: AUTHORITATIVE

## Documentation Dependency Graph

- start_here.md -> []
- read_this_first.md -> []
- mental_model.md -> read_this_first.md
- execution_flow.md -> mental_model.md
- state_and_artifacts.md -> execution_flow.md
- trace_format.md -> state_and_artifacts.md
- trace_lifecycle.md -> trace_format.md
- core_contracts.md -> trace_lifecycle.md
- system_contract.md -> core_contracts.md
- determinism.md -> core_contracts.md
- verification_model.md -> core_contracts.md, trace_format.md
- failure_semantics.md -> verification_model.md
- security_model.md -> core_contracts.md
- versioning_compat.md -> core_contracts.md
- release_scope_v0_1_0.md -> system_contract.md
- architecture.md -> execution_flow.md
- benchmarks.md -> architecture.md
- misuse_cases.md -> core_contracts.md
- doc_invariants.md -> system_contract.md
- doc_to_code_map.md -> doc_invariants.md
- maintainer_rules.md -> doc_invariants.md
- contributor_reading_order.md -> doc_invariants.md
