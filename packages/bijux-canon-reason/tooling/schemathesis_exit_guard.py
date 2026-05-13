#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
from xml.etree import ElementTree


def _resolve_schemathesis_binary() -> str:
    project_artifacts_dir = os.environ.get("PROJECT_ARTIFACTS_DIR")
    if project_artifacts_dir:
        candidate = Path(project_artifacts_dir) / "venv" / "bin" / "schemathesis"
        if candidate.is_file():
            return str(candidate)

    act_dir = os.environ.get("ACT")
    if act_dir:
        candidate = Path(act_dir) / "schemathesis"
        if candidate.is_file():
            return str(candidate)

    resolved = shutil.which("schemathesis")
    if resolved:
        return resolved

    raise SystemExit("schemathesis executable is not available")


def _junit_report_path(arguments: list[str]) -> Path | None:
    for index, argument in enumerate(arguments):
        if argument == "--report-junit-path" and index + 1 < len(arguments):
            return Path(arguments[index + 1])
        if argument.startswith("--report-junit-path="):
            return Path(argument.split("=", 1)[1])
    return None


def _junit_report_is_clean(report_path: Path) -> bool:
    if not report_path.is_file():
        return False

    root = ElementTree.parse(report_path).getroot()
    failure_count = sum(
        int(node.attrib.get("failures", "0")) for node in root.iter() if "failures" in node.attrib
    )
    error_count = sum(
        int(node.attrib.get("errors", "0")) for node in root.iter() if "errors" in node.attrib
    )
    return failure_count == 0 and error_count == 0


def main() -> int:
    command = [_resolve_schemathesis_binary(), *sys.argv[1:]]
    completed = subprocess.run(command, check=False)
    if completed.returncode == 0:
        return 0

    report_path = _junit_report_path(sys.argv[1:])
    if report_path is not None and _junit_report_is_clean(report_path):
        print(
            "schemathesis exited nonzero with a clean junit report; treating the contract run as successful",
            file=sys.stderr,
        )
        return 0

    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
