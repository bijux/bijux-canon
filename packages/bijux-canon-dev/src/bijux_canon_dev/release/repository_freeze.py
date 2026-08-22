"""Create a restorable ZIP snapshot from one tracked Git revision."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import zipfile


class RepositoryFreezeError(RuntimeError):
    """A repository revision could not be frozen safely."""


def _run_git(
    repository: Path,
    *arguments: str,
    text: bool = True,
) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(
        ("git", "-C", str(repository), *arguments),
        capture_output=True,
        check=False,
        text=text,
    )
    if completed.returncode != 0:
        stderr = completed.stderr if text else completed.stderr.decode(errors="replace")
        raise RepositoryFreezeError(
            f"git {' '.join(arguments)} failed: {stderr.strip()}"
        )
    return completed


def _git_text(repository: Path, *arguments: str) -> str:
    completed = _run_git(repository, *arguments)
    assert isinstance(completed.stdout, str)
    return completed.stdout.strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _zip_info(name: str, commit_timestamp: int) -> zipfile.ZipInfo:
    committed_at = datetime.fromtimestamp(commit_timestamp, tz=UTC)
    year = min(max(committed_at.year, 1980), 2107)
    info = zipfile.ZipInfo(
        name,
        (
            year,
            committed_at.month,
            committed_at.day,
            committed_at.hour,
            committed_at.minute,
            committed_at.second,
        ),
    )
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def _create_history_bundle(
    repository: Path,
    commit: str,
    workspace: Path,
) -> Path:
    history_repository = workspace / "history.git"
    _run_git(workspace, "init", "--quiet", "--bare", str(history_repository))
    _run_git(
        history_repository,
        "fetch",
        "--quiet",
        "--no-tags",
        str(repository),
        f"{commit}:refs/heads/frozen",
    )
    _run_git(history_repository, "symbolic-ref", "HEAD", "refs/heads/frozen")
    bundle = workspace / "git-history.bundle"
    _run_git(
        history_repository,
        "bundle",
        "create",
        str(bundle),
        "--all",
    )
    _run_git(repository, "bundle", "verify", str(bundle))
    return bundle


def freeze_repository(repository: Path, revision: str = "HEAD") -> Path:
    """Freeze ``revision`` as tracked files plus its complete reachable history."""
    repository = repository.resolve()
    if not repository.is_dir():
        raise RepositoryFreezeError(f"repository does not exist: {repository}")

    top_level = Path(_git_text(repository, "rev-parse", "--show-toplevel")).resolve()
    if top_level != repository:
        raise RepositoryFreezeError(
            f"repository must be its Git top level: {repository} != {top_level}"
        )

    commit = _git_text(
        repository,
        "rev-parse",
        "--verify",
        "--end-of-options",
        f"{revision}^{{commit}}",
    )
    short_commit = commit[:8]
    commit_count = int(_git_text(repository, "rev-list", "--count", commit))
    commit_timestamp = int(_git_text(repository, "show", "-s", "--format=%ct", commit))
    tracked_entries = tuple(
        line
        for line in _git_text(
            repository, "ls-tree", "-r", "--name-only", commit
        ).splitlines()
        if line
    )

    stem = f"{repository.name}-{commit_count}-{short_commit}"
    output_directory = repository / "artifacts" / "freeze"
    output_directory.mkdir(parents=True, exist_ok=True)
    output = output_directory / f"{stem}.zip"

    with tempfile.TemporaryDirectory(
        prefix=f".{stem}-", dir=output_directory
    ) as temporary_directory:
        workspace = Path(temporary_directory)
        candidate = workspace / output.name
        _run_git(
            repository,
            "archive",
            "--format=zip",
            f"--prefix={stem}/repository/",
            f"--output={candidate}",
            commit,
        )
        bundle = _create_history_bundle(repository, commit, workspace)
        manifest = {
            "archive_format": "git-tracked-tree-and-reachable-history",
            "commit": commit,
            "commit_count": commit_count,
            "git_history": {
                "bundle_path": f"{stem}/git-history.bundle",
                "head": "refs/heads/frozen",
                "scope": "commit-and-all-reachable-ancestors",
                "sha256": _sha256(bundle),
            },
            "repository": repository.name,
            "schema_version": 1,
            "short_commit": short_commit,
            "tracked_entry_count": len(tracked_entries),
            "tree_path": f"{stem}/repository/",
        }
        manifest_bytes = (
            json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8") + b"\n"
        )

        with zipfile.ZipFile(candidate, mode="a") as archive:
            bundle_info = _zip_info(f"{stem}/git-history.bundle", commit_timestamp)
            bundle_info.compress_type = zipfile.ZIP_STORED
            archive.writestr(bundle_info, bundle.read_bytes())
            manifest_info = _zip_info(f"{stem}/FREEZE.json", commit_timestamp)
            manifest_info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(manifest_info, manifest_bytes)

        with zipfile.ZipFile(candidate) as archive:
            corrupt_member = archive.testzip()
            if corrupt_member is not None:
                raise RepositoryFreezeError(
                    f"generated ZIP contains a corrupt member: {corrupt_member}"
                )
        os.replace(candidate, output)

    return output


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Freeze one tracked repository revision and its reachable Git history."
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path.cwd(),
        help="Git repository root (default: current directory)",
    )
    parser.add_argument(
        "--ref",
        default="HEAD",
        help="Commit, branch, or tag to freeze (default: HEAD)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the repository freeze command."""
    parser = _parser()
    arguments = parser.parse_args(argv)
    try:
        output = freeze_repository(arguments.repo, arguments.ref)
    except RepositoryFreezeError as exc:
        parser.error(str(exc))
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
