from __future__ import annotations

import json
from pathlib import Path

import pytest

from bijux_canon_dev.security import pip_audit_gate


def test_gate_rejects_ungoverned_ignore_ids(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(pip_audit_gate, "IGNORE_IDS", {"PYSEC-2099-1"})

    assert pip_audit_gate.main() == 2
    assert "ungoverned dependency vulnerability suppressions" in capsys.readouterr().out


def test_gate_fails_a_vulnerable_dependency(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    report = tmp_path / "pip-audit.json"
    report.write_text(
        json.dumps(
            {
                "dependencies": [
                    {
                        "name": "example",
                        "version": "1.0",
                        "vulns": [
                            {
                                "id": "PYSEC-2099-1",
                                "aliases": ["CVE-2099-0001"],
                                "fix_versions": ["1.1"],
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(pip_audit_gate, "IGNORE_IDS", set())
    monkeypatch.setattr(pip_audit_gate, "REPORT_PATH", str(report))
    monkeypatch.setattr(pip_audit_gate, "IS_STRICT", True)

    assert pip_audit_gate.main() == 1
    output = capsys.readouterr().out
    assert "CVE-2099-0001" in output
    assert "example" in output


def test_gate_accepts_a_report_without_vulnerabilities(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    report = tmp_path / "pip-audit.json"
    report.write_text(
        json.dumps(
            {"dependencies": [{"name": "example", "version": "1.1", "vulns": []}]}
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(pip_audit_gate, "IGNORE_IDS", set())
    monkeypatch.setattr(pip_audit_gate, "REPORT_PATH", str(report))
    monkeypatch.setattr(pip_audit_gate, "IS_STRICT", True)

    assert pip_audit_gate.main() == 0
    assert "0 vulnerabilities found" in capsys.readouterr().out
