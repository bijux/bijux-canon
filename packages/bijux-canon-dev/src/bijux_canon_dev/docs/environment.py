"""Install only Canon's locked documentation tools in an owned environment."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ENVIRONMENT = "artifacts/root/docs/venv"
OWNERSHIP = {
    "schema": 1,
    "purpose": "canon-documentation-publication",
    "environment": ENVIRONMENT,
}


def environment_path(root: Path) -> Path:
    root = root.resolve()
    selected = root
    for component in Path(ENVIRONMENT).parts:
        selected /= component
        if selected.is_symlink():
            raise ValueError("Documentation environment cannot contain symlinks")
    if selected.exists() and not selected.is_dir():
        raise ValueError("Documentation environment must be a directory")
    return selected


def install(root: Path, python: str, uv: str) -> None:
    """Preserve other environments and never install editable application packages."""
    selected = environment_path(root)
    products = {
        name: root.resolve() / ("artifacts/root/docs/" + name)
        for name in ("uv-cache", "process")
    }
    for product in products.values():
        if product.is_symlink() or (product.exists() and not product.is_dir()):
            raise ValueError(
                "Documentation process/cache path must be an owned directory"
            )
    marker = selected / ".ownership.json"
    if selected.exists():
        if (
            marker.is_symlink()
            or not marker.is_file()
            or json.loads(marker.read_text()) != OWNERSHIP
        ):
            raise ValueError("Preserve unowned documentation environment")
    else:
        selected.mkdir(parents=True)
        marker.write_text(json.dumps(OWNERSHIP, sort_keys=True) + "\n")
    for product in products.values():
        product.mkdir(parents=True, exist_ok=True)
    environment = dict(
        os.environ,
        PYTHONDONTWRITEBYTECODE="1",
        UV_PROJECT_ENVIRONMENT=str(selected),
        UV_CACHE_DIR=str(products["uv-cache"]),
        TMPDIR=str(products["process"]),
        UV_PYTHON_DOWNLOADS="never",
    )
    # stdlib venv introduces no virtualenv startup hook or bundled pip inventory.
    # Partial command-owned creation can resume without clearing existing bytes.
    if not (selected / "bin/python").exists():
        subprocess.run(
            [python, "-m", "venv", "--without-pip", str(selected)],
            cwd=root,
            env=environment,
            check=True,
        )
    # --locked validates metadata and rejects drift without rewriting uv.lock.
    subprocess.run(
        [
            uv,
            "sync",
            "--locked",
            "--only-group",
            "docs",
            "--no-install-workspace",
            "--python",
            python,
        ],
        cwd=root,
        env=environment,
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", required=True)
    parser.add_argument("--uv", default="uv")
    args = parser.parse_args()
    try:
        install(Path.cwd(), args.python, args.uv)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Canon documentation environment rejected: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
