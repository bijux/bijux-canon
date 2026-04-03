from __future__ import annotations

import argparse
import subprocess
import tomllib
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resolve a package version from pyproject metadata or package tags."
    )
    parser.add_argument("--pyproject", required=True, help="Path to pyproject.toml")
    parser.add_argument("--package-name", required=True, help="Package slug/tag prefix")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project = tomllib.loads(Path(args.pyproject).read_text()).get("project", {})
    version = project.get("version")
    if version:
        print(version)
        return 0

    tag = subprocess.run(
        ["git", "tag", "--sort=v:refname", "--list", f"{args.package_name}/v*"],
        capture_output=True,
        check=False,
        text=True,
    )
    tags = [line.strip() for line in tag.stdout.splitlines() if line.strip()]
    print(tags[-1].removeprefix(f"{args.package_name}/v") if tags else "0.0.0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
