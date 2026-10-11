"""Bind Canon's documentation commands to one qualified public artifact."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

SITE_URL = "https://bijux.io/bijux-canon/"
SITE_DIR = "artifacts/root/docs/build-site"
STANDARD_ROOT = "artifacts/website-security/standard-authorities"
SOURCE_RECEIPT = "artifacts/website-security/source-identity.json"
MANIFEST = "artifacts/website-security/publication-manifest.json"
STANDARD_ORIGIN = "https://github.com/bijux/bijux-std.git"


def validate_selection(site_url: str, site_dir: str) -> None:
    """Reject another product, development origin or output before mutation."""
    if site_url != SITE_URL:
        raise ValueError(f"Canon publication requires exact production URL {SITE_URL}")
    if site_dir != SITE_DIR:
        raise ValueError(f"Canon publication requires exact artifact {SITE_DIR}")
    for name in ("BIJUX_STD_LOCAL_VERIFY", "BIJUX_STD_ALLOW_LOCAL_SOURCE"):
        if os.environ.get(name) == "1":
            raise ValueError("Canon publication cannot use local candidate authority")


def command(root: Path, *arguments: str, authority: str | None = None) -> None:
    """Use the same renderer and production environment for every boundary."""
    environment = dict(
        os.environ,
        PYTHONDONTWRITEBYTECODE="1",
        SITE_URL=SITE_URL,
        DOCS_BUILD_SITE_URL=SITE_URL,
        DOCS_SITE_DIR=SITE_DIR,
        DOCS_SOURCE_IDENTITY=SOURCE_RECEIPT,
        DOCS_PYTHON=sys.executable,
    )
    if authority is None:
        environment.pop("BIJUX_STD_ROOT", None)
    else:
        environment["BIJUX_STD_ROOT"] = str(root / authority)
    subprocess.run(list(arguments), cwd=root, env=environment, check=True)


def accepted_standard(root: Path, pin: str) -> str:
    """Keep immutable pins separate and resume only this command's empty cache."""
    if re.fullmatch(r"[0-9a-f]{40}", pin) is None:
        raise ValueError("Canon publication cache requires an exact standard SHA")
    relative = f"{STANDARD_ROOT}/{pin}"
    destination = root / relative
    ownership = root / STANDARD_ROOT / ".ownership" / f"{pin}.json"
    for selected in (destination, ownership, destination / ".git"):
        current = root
        for component in selected.relative_to(root).parts:
            current /= component
            if current.is_symlink():
                raise ValueError(
                    "Canon publication standard cache cannot contain symlinks"
                )
    expected = {
        "schema": 1,
        "path": relative,
        "pin": pin,
        "origin": STANDARD_ORIGIN,
        "scope": "command-owned-cache-only",
    }
    owned = ownership.is_file() and json.loads(ownership.read_text()) == expected
    if destination.exists() and not destination.is_dir():
        raise ValueError("Canon publication standard cache must be a directory")
    if destination.exists():
        repository = subprocess.run(
            ["git", "-C", str(destination), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
        )
        if (
            repository.returncode
            or Path(repository.stdout.strip()).resolve() != destination.resolve()
        ):
            if not owned or any(destination.iterdir()):
                raise ValueError(
                    "Preserve existing unowned or incomplete standard cache"
                )
        else:
            status = subprocess.check_output(
                [
                    "git",
                    "-C",
                    str(destination),
                    "status",
                    "--porcelain",
                    "--untracked-files=all",
                ],
                text=True,
            )
            if status:
                raise ValueError(
                    "Preserve dirty standard cache without fetching or resetting"
                )
            origin = subprocess.run(
                ["git", "-C", str(destination), "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
            )
            if origin.returncode == 0 and origin.stdout.strip() != STANDARD_ORIGIN:
                raise ValueError(
                    "Standard cache origin differs from the official source"
                )
            head = subprocess.run(
                [
                    "git",
                    "-C",
                    str(destination),
                    "rev-parse",
                    "--verify",
                    "HEAD^{commit}",
                ],
                capture_output=True,
                text=True,
            )
            if head.returncode == 0:
                if head.stdout.strip() != pin or origin.returncode:
                    raise ValueError("Preserve standard checkout with another identity")
                # Independent source capture rechecks the fetched authority.
                return relative
            if not owned:
                raise ValueError(
                    "Preserve unowned standard cache without a committed identity"
                )
    elif not owned:
        ownership.parent.mkdir(parents=True, exist_ok=True)
        # Ownership permits resuming initialization; it is never release approval.
        with ownership.open("x", encoding="utf-8") as record:
            record.write(json.dumps(expected, sort_keys=True) + "\n")
    if not (destination / ".git").is_dir():
        command(root, "git", "init", "--quiet", str(destination), authority=relative)
    origin = subprocess.run(
        ["git", "-C", str(destination), "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
    )
    if origin.returncode:
        command(
            root,
            "git",
            "-C",
            str(destination),
            "remote",
            "add",
            "origin",
            STANDARD_ORIGIN,
            authority=relative,
        )
    elif origin.stdout.strip() != STANDARD_ORIGIN:
        raise ValueError("Standard cache origin differs from the official source")
    command(
        root,
        "git",
        "-C",
        str(destination),
        "fetch",
        "--quiet",
        "--depth=1",
        "origin",
        pin,
        authority=relative,
    )
    command(
        root,
        "git",
        "-C",
        str(destination),
        "checkout",
        "--quiet",
        "--detach",
        pin,
        authority=relative,
    )
    return relative


def build(root: Path) -> None:
    """Create honest source, renderer, CSP, route and publication receipts."""
    shared = root / ".bijux/shared/bijux-docs"
    spec = importlib.util.spec_from_file_location(
        "canon_docs_source_identity", shared / "security/build_identity.py"
    )
    if spec is None or spec.loader is None:
        raise ValueError("Refresh accepted shared publication tooling before building")
    identity = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(identity)
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()
    source_sha = os.environ.get("GITHUB_SHA", head)
    identity.clean_source(root, source_sha)
    pin = identity.regular(root, ".github/standards/bijux-docs.sha").read_text().strip()
    if re.fullmatch(r"[0-9a-f]{40}", pin) is None:
        raise ValueError(
            "Canon publication requires a tracked full accepted standard SHA"
        )
    authority = accepted_standard(root, pin)
    producer = shared / "security/render_publication.py"
    publisher = shared / "security/publication.py"
    # The projector consumes context exported by the existing accepted-source
    # guard. Keep that guard and the selected renderer in the same child process.
    projection = (
        "set -euo pipefail\n"
        'source "$1/tooling/scripts/docs_source_authority.sh"\n'
        'verify_docs_authority "$2" "$1"\n'
        'exec "$3" "$1/tooling/scripts/project_bijux_docs.py" "$2" "$1" --check\n'
    )
    command(
        root,
        "bash",
        "-c",
        projection,
        "canon-docs-projection",
        str(shared),
        str(root),
        sys.executable,
        authority=authority,
    )
    command(
        root,
        sys.executable,
        str(shared / "security/build_identity.py"),
        "capture-source",
        "--standard-pin",
        "publication",
        "--source-sha",
        source_sha,
        "--standard-root",
        authority,
        "--site-url",
        SITE_URL,
        "--site-dir",
        SITE_DIR,
        "--config",
        "mkdocs.yml",
        "--build-command",
        "make gh-docs-build",
        "--verify-command",
        "make gh-docs-verify",
        "--output",
        SOURCE_RECEIPT,
        authority=authority,
    )
    command(
        root,
        sys.executable,
        str(producer),
        "--config",
        "mkdocs.yml",
        "--site-dir",
        SITE_DIR,
        "--site-url",
        SITE_URL,
        "--source-identity",
        SOURCE_RECEIPT,
        authority=authority,
    )
    command(
        root,
        "bash",
        str(shared / "tooling/scripts/verify_bijux_docs_site.sh"),
        authority=authority,
    )
    command(
        root,
        sys.executable,
        str(publisher),
        "--repo-root",
        str(root),
        "admit",
        "--site-dir",
        SITE_DIR,
        "--site-url",
        SITE_URL,
        "--source-sha",
        source_sha,
        "--standard-sha",
        pin,
        "--source-identity",
        SOURCE_RECEIPT,
        "--build-identity",
        "artifacts/website-security/build-identity.json",
        "--verification-report",
        "artifacts/website-security/site-verification.json",
        "--csp-report",
        "artifacts/website-security/csp.json",
        "--output",
        MANIFEST,
        authority=authority,
    )


def verify(root: Path) -> None:
    """Recheck the same receipts and bytes without rebuilding or rewriting them."""
    command(
        root,
        sys.executable,
        str(root / ".bijux/shared/bijux-docs/security/publication.py"),
        "--repo-root",
        str(root),
        "verify",
        "--manifest",
        MANIFEST,
        "--require-qualified",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("build", "verify"))
    parser.add_argument("--site-url", required=True)
    parser.add_argument("--site-dir", required=True)
    args = parser.parse_args()
    try:
        validate_selection(args.site_url, args.site_dir)
        root = Path.cwd().resolve()
        if args.operation == "build":
            build(root)
        else:
            verify(root)
    except (OSError, ValueError, ImportError, subprocess.CalledProcessError) as error:
        print(f"Canon documentation publication rejected: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
