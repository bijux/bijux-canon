# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from pathlib import Path

DOCS = {
    "docs/spec/core_contracts.md": ["span+hash", "replay", "artifact"],
    "docs/spec/architecture.md": ["flow", "plan", "trace"],
    "docs/spec/trace_format.md": ["trace_schema_version", "event", "hash"],
    "docs/spec/verification_model.md": ["verificationreport", "fail-closed", "insufficient"],
    "docs/spec/mental_model.md": ["pipeline", "evidence", "verification"],
    "docs/spec/security_model.md": ["threat", "replay", "path"],
    "docs/spec/execution_flow.md": ["problem", "trace", "verification"],
    "docs/spec/state_and_artifacts.md": ["artifacts", "runtime state", "derivations"],
    "docs/spec/trace_lifecycle.md": ["sealed", "replayed", "immutable"],
    "docs/spec/failure_semantics.md": ["validation", "verification", "fatal"],
    "docs/spec/determinism.md": ["deterministic", "sha256", "tokenization"],
    "docs/spec/versioning_compat.md": ["trace_schema_version", "breaking", "upgrade"],
    "docs/spec/read_this_first.md": ["who", "not", "before"],
    "docs/spec/doc_invariants.md": ["one concept", "invariants", "soft language"],
    "docs/spec/system_contract.md": ["determinism", "evidence", "replay"],
    "docs/maintainer/maintainer_rules.md": ["mandatory", "fail", "reject"],
    "docs/maintainer/forbidden_changes.md": ["never", "breaking", "reject"],
    "docs/maintainer/why_this_is_hard.md": ["fragile", "determinism", "verification"],
    "docs/maintainer/glossary.md": ["terms", "locked", "vocabulary"],
    "docs/maintainer/security_policy.md": ["report", "contact", "scope"],
    "docs/maintainer/tests.md": ["required", "coverage", "benchmarks"],
    "docs/user/usage.md": ["cli", "run", "verify"],
}


def test_docs_exist_and_contain_keywords() -> None:
    root = Path(__file__).resolve().parents[2]
    for name, keywords in DOCS.items():
        p = root / name
        assert p.exists(), f"missing doc {name}"
        data = p.read_text(encoding="utf-8").lower()
        for kw in keywords:
            assert kw.lower() in data, f"{name} missing keyword {kw}"


def test_no_soft_language_in_core_docs() -> None:
    root = Path(__file__).resolve().parents[2]
    soft_words = {"should", "typically", "generally", "allows"}
    for name in DOCS:
        data = (root / name).read_text(encoding="utf-8").lower()
        for word in soft_words:
            assert word not in data, f"{name} contains soft language: {word}"


def test_non_negotiable_sections_present() -> None:
    root = Path(__file__).resolve().parents[2]
    required_marker = "non-negotiable invariants"
    for name in (
        "docs/spec/core_contracts.md",
        "docs/spec/trace_format.md",
        "docs/spec/verification_model.md",
    ):
        data = (root / name).read_text(encoding="utf-8").lower()
        assert required_marker in data, f"{name} missing {required_marker}"


def test_status_headers_present() -> None:
    root = Path(__file__).resolve().parents[2]
    allowed = {"STATUS: AUTHORITATIVE", "STATUS: EXPLANATORY"}
    for name in DOCS:
        data = (root / name).read_text(encoding="utf-8")
        lines = data.splitlines()
        statuses = [ln.strip() for ln in lines if "STATUS:" in ln]
        assert statuses, f"{name} missing STATUS header"
        for st in statuses:
            assert st in allowed, f"{name} has invalid STATUS value: {st}"


def test_doc_to_code_map_exists() -> None:
    root = Path(__file__).resolve().parents[2]
    p = root / "docs" / "spec" / "doc_to_code_map.md"
    assert p.exists(), "doc_to_code_map.md missing"


def test_doc_dependency_exists() -> None:
    root = Path(__file__).resolve().parents[2]
    p = root / "docs" / "spec" / "doc_dependency.md"
    assert p.exists(), "doc_dependency.md missing"
