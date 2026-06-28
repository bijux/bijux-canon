from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_ingest_security_subtargets_bootstrap_package_environment() -> None:
    profile = (REPO_ROOT / "makes" / "packages" / "bijux-canon-ingest.mk").read_text(
        encoding="utf-8"
    )

    assert "security-bandit" in profile
    assert "security-audit" in profile
    assert "security-deps" in profile


def test_compat_packages_install_security_tooling_without_stamp_shortcuts() -> None:
    profile = (REPO_ROOT / "makes" / "packages" / "compat-package.mk").read_text(
        encoding="utf-8"
    )

    assert "PACKAGE_INSTALL_STAMP ?=" not in profile
    assert "security-bandit" in profile
    assert "security-audit" in profile
    assert "security-deps" in profile
