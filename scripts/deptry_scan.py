#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run deptry with repository-owned config merged into a package pyproject.toml.",
    )
    parser.add_argument("--config", required=True, help="Path to the repo-owned deptry TOML file.")
    parser.add_argument("--project-dir", required=True, help="Path to the package root containing pyproject.toml.")
    parser.add_argument("--deptry-bin", default="deptry", help="Deptry executable to invoke.")
    parser.add_argument("roots", nargs="*", default=["."], help="Roots to scan, relative to the project dir.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_dir = Path(args.project_dir).resolve()
    config_path = Path(args.config).resolve()
    pyproject_path = project_dir / "pyproject.toml"

    if not pyproject_path.is_file():
        raise SystemExit(f"pyproject.toml not found in {project_dir}")
    if not config_path.is_file():
        raise SystemExit(f"deptry config not found at {config_path}")

    deptry_bin = shutil.which(args.deptry_bin)
    if deptry_bin is None:
        raise SystemExit(f"deptry executable not found: {args.deptry_bin}")

    pyproject_text = pyproject_path.read_text(encoding="utf-8").rstrip()
    config_text = config_path.read_text(encoding="utf-8").strip()
    merged_text = f"{pyproject_text}\n\n{config_text}\n"

    with tempfile.TemporaryDirectory(prefix="deptry-") as tmpdir:
        merged_pyproject = Path(tmpdir) / "pyproject.toml"
        merged_pyproject.write_text(merged_text, encoding="utf-8")

        command = [
            deptry_bin,
            "--config",
            os.fspath(merged_pyproject),
            *args.roots,
        ]
        completed = subprocess.run(command, cwd=project_dir, check=False)
        return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
