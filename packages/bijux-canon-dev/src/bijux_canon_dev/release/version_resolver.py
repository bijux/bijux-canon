from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resolve a package version from pyproject metadata or package tags."
    )
    parser.add_argument("--pyproject", required=True, help="Path to pyproject.toml")
    parser.add_argument("--package-name", required=True, help="Package slug/tag prefix")
    return parser.parse_args()


def resolve_version(pyproject_path: Path, package_name: str) -> str:
    project = tomllib.loads(pyproject_path.read_text(encoding="utf-8")).get("project", {})
    version = project.get("version")
    if isinstance(version, str) and version:
        return version

    tag_process = subprocess.run(
        ["git", "tag", "--sort=v:refname", "--list", f"{package_name}/v*"],
        capture_output=True,
        check=False,
        text=True,
    )
    tags = [line.strip() for line in tag_process.stdout.splitlines() if line.strip()]
    if tags:
        return tags[-1].removeprefix(f"{package_name}/v")
    return "0.0.0"


def main() -> int:
    args = parse_args()
    print(resolve_version(Path(args.pyproject), args.package_name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
