from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[5]
MODULE_PATH = (
    REPO_ROOT
    / "packages"
    / "bijux-canon-reason"
    / "tooling"
    / "schemathesis_exit_guard.py"
)

_SPEC = spec_from_file_location("schemathesis_exit_guard", MODULE_PATH)
assert _SPEC is not None
assert _SPEC.loader is not None
_MODULE = module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


def test_schemathesis_exit_guard_accepts_clean_junit_reports(tmp_path: Path) -> None:
    report_path = tmp_path / "schemathesis.xml"
    report_path.write_text('<testsuite failures="0" errors="0" tests="3" />', encoding="utf-8")

    assert _MODULE._junit_report_is_clean(report_path)


def test_schemathesis_exit_guard_rejects_failed_junit_reports(tmp_path: Path) -> None:
    report_path = tmp_path / "schemathesis.xml"
    report_path.write_text('<testsuite failures="1" errors="0" tests="3" />', encoding="utf-8")

    assert not _MODULE._junit_report_is_clean(report_path)


def test_reason_package_make_uses_repo_owned_schemathesis_exit_guard() -> None:
    package_make = (
        REPO_ROOT / "makes" / "packages" / "bijux-canon-reason.mk"
    ).read_text(encoding="utf-8")

    assert "SCHEMATHESIS = $(PROJECT_DIR)/tooling/schemathesis_exit_guard.py" in package_make
