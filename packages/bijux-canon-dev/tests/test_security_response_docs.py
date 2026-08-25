from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
RUNBOOK = REPO_ROOT / "docs/01-bijux-canon/operations/security-response.md"


def test_security_runbook_maps_every_durable_control_family() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")

    for authority in (
        "packages/bijux-canon-agent/tests/integration/test_untrusted_retrieved_content.py",
        "packages/bijux-canon-ingest/tests/unit/infra/adapters/test_directory_source.py",
        "packages/bijux-canon-ingest/tests/unit/infra/adapters/test_file_admission.py",
        "packages/bijux-canon-ingest/tests/unit/infra/adapters/test_parser_admission_security.py",
        "packages/bijux-canon-runtime/tests/unit/application/test_secret_provider_security.py",
        "packages/bijux-canon-runtime/tests/unit/runtime/test_publication_transactions.py",
        "packages/bijux-canon-index/tests/unit/application/test_index_activation.py",
        "packages/bijux-canon-runtime/tests/unit/runtime/test_durable_jobs.py",
        "packages/bijux-canon-dev/tests/test_pip_audit_gate.py",
        "packages/bijux-canon-dev/tests/test_root_tooling_contract.py",
        "packages/bijux-canon-dev/tests/test_supply_chain.py",
    ):
        assert authority in text
        assert (REPO_ROOT / authority).is_file()


def test_security_runbook_is_discoverable_from_policy_and_site_navigation() -> None:
    security_policy = (REPO_ROOT / "SECURITY.md").read_text(encoding="utf-8")
    operations = (REPO_ROOT / "docs/01-bijux-canon/operations/index.md").read_text(
        encoding="utf-8"
    )
    navigation = (REPO_ROOT / "mkdocs.yml").read_text(encoding="utf-8")

    assert "operations/security-response.md" in security_policy
    assert (
        "[Security Evidence and Incident Response](security-response.md)" in operations
    )
    assert "01-bijux-canon/operations/security-response.md" in navigation


def test_security_runbook_preserves_honesty_boundaries() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")

    assert "unsigned local attestations" in text
    assert "current repository retains no OCI container build definition" in text
    assert "Ordinary `artifacts/` content is disposable" in text
    assert "do not\n  prove safety for every possible byte sequence" in text
