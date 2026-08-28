from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

import pytest

from bijux_canon_dev.release.repository_freeze import (
    RepositoryFreezeError,
    freeze_repository,
)


def _git(repository: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ("git", "-C", str(repository), *arguments),
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _repository(tmp_path: Path) -> tuple[Path, str]:
    repository = tmp_path / "example"
    repository.mkdir()
    _git(repository, "init", "--quiet")
    _git(repository, "config", "user.email", "freeze@example.invalid")
    _git(repository, "config", "user.name", "Freeze Test")
    (repository / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
    (repository / "tracked.txt").write_text("first\n", encoding="utf-8")
    _git(repository, "add", ".gitignore", "tracked.txt")
    _git(repository, "commit", "--quiet", "-m", "first")
    first_commit = _git(repository, "rev-parse", "HEAD")
    (repository / "tracked.txt").write_text("second\n", encoding="utf-8")
    (repository / "second.txt").write_text("tracked later\n", encoding="utf-8")
    _git(repository, "add", "tracked.txt", "second.txt")
    _git(repository, "commit", "--quiet", "-m", "second")
    (repository / "untracked.txt").write_text("never archive me\n", encoding="utf-8")
    (repository / "ignored.txt").write_text(
        "never archive me either\n", encoding="utf-8"
    )
    return repository, first_commit


def test_freeze_contains_selected_tree_and_reachable_history(tmp_path: Path) -> None:
    repository, first_commit = _repository(tmp_path)

    output = freeze_repository(repository, first_commit)

    assert output.name == f"example-1-{first_commit[:8]}.zip"
    stem = output.stem
    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
        assert f"{stem}/repository/tracked.txt" in names
        assert f"{stem}/repository/second.txt" not in names
        assert f"{stem}/repository/untracked.txt" not in names
        assert f"{stem}/repository/ignored.txt" not in names
        assert archive.read(f"{stem}/repository/tracked.txt") == b"first\n"
        manifest = json.loads(archive.read(f"{stem}/FREEZE.json"))
        bundle = tmp_path / "restorable.bundle"
        bundle.write_bytes(archive.read(f"{stem}/git-history.bundle"))

    assert manifest["commit"] == first_commit
    assert manifest["commit_count"] == 1
    assert manifest["tracked_entry_count"] == 2
    assert manifest["git_history"]["scope"] == ("commit-and-all-reachable-ancestors")
    assert _git(repository, "bundle", "verify", str(bundle))
    assert set(_git(repository, "bundle", "list-heads", str(bundle)).splitlines()) == {
        f"{first_commit} HEAD",
        f"{first_commit} refs/heads/frozen",
    }
    checkout = tmp_path / "checkout"
    _git(tmp_path, "clone", "--quiet", str(bundle), str(checkout))
    assert _git(checkout, "rev-parse", "HEAD") == first_commit
    assert (checkout / "tracked.txt").read_text(encoding="utf-8") == "first\n"

    first_archive_sha256 = hashlib.sha256(output.read_bytes()).hexdigest()
    repeated_output = freeze_repository(repository, "HEAD~1")
    assert repeated_output == output
    assert hashlib.sha256(repeated_output.read_bytes()).hexdigest() == (
        first_archive_sha256
    )


def test_freeze_rejects_an_unknown_revision(tmp_path: Path) -> None:
    repository, _ = _repository(tmp_path)

    with pytest.raises(RepositoryFreezeError, match="rev-parse"):
        freeze_repository(repository, "missing-revision")


def test_freeze_requires_the_repository_top_level(tmp_path: Path) -> None:
    repository, _ = _repository(tmp_path)
    child = repository / "child"
    child.mkdir()

    with pytest.raises(RepositoryFreezeError, match="Git top level"):
        freeze_repository(child)
