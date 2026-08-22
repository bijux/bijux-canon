from __future__ import annotations

import json
from pathlib import Path
import subprocess
import time

import pytest

from bijux_canon_dev.release.frozen_gate import (
    GATE_COMMANDS,
    FrozenGateError,
    launch_frozen_gate,
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
    _git(repository, "config", "user.email", "frozen@example.invalid")
    _git(repository, "config", "user.name", "Frozen Gate Test")
    (repository / ".gitignore").write_text("artifacts/\nignored.txt\n")
    (repository / "Makefile").write_text(
        ".PHONY: test-all\n"
        "test-all:\n"
        "\t@mkdir -p artifacts\n"
        "\t@printf 'frozen gate passed\\n' > artifacts/outcome.txt\n"
    )
    _git(repository, "add", ".gitignore", "Makefile")
    _git(repository, "commit", "--quiet", "-m", "first")
    first_commit = _git(repository, "rev-parse", "HEAD")
    (repository / "Makefile").write_text("test-all:\n\t@exit 9\n")
    _git(repository, "add", "Makefile")
    _git(repository, "commit", "--quiet", "-m", "second")
    (repository / "ignored.txt").write_text("not frozen\n")
    (repository / "untracked.txt").write_text("not frozen\n")
    return repository, first_commit


def _wait_for_status(path: Path) -> int:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if path.is_file():
            return int(path.read_text(encoding="utf-8").strip())
        time.sleep(0.05)
    raise AssertionError(f"frozen gate did not finish: {path}")


def test_frozen_gate_runs_selected_tracked_revision_in_background(
    tmp_path: Path,
) -> None:
    repository, first_commit = _repository(tmp_path)

    launch = launch_frozen_gate(repository, first_commit, "test-all")

    status_file = Path(launch.status_file)
    assert _wait_for_status(status_file) == 0
    source = Path(launch.repository)
    assert _git(source, "rev-parse", "HEAD") == first_commit
    assert (source / "artifacts/outcome.txt").read_text() == "frozen gate passed\n"
    assert not (source / "ignored.txt").exists()
    assert not (source / "untracked.txt").exists()
    metadata = json.loads(Path(launch.metadata_file).read_text(encoding="utf-8"))
    assert metadata["commit"] == first_commit
    assert metadata["commit_count"] == 1
    assert metadata["commands"] == [["make", "--no-print-directory", "test-all"]]
    assert metadata["pid"] == launch.pid


def test_frozen_gate_defines_independent_complete_gate_commands() -> None:
    assert set(GATE_COMMANDS) == {"ci-github", "test-all", "tox"}
    assert GATE_COMMANDS["test-all"][-1][-1] == "test-all"
    assert GATE_COMMANDS["tox"][-1][-2:] == ("-m", "tox")
    assert GATE_COMMANDS["ci-github"][0][-4:] == (
        "check-shared-bijux-py",
        "check-config-layout",
        "check-make-layout",
        "help",
    )
    assert GATE_COMMANDS["ci-github"][-1][-2:] == ("-m", "tox")


def test_frozen_gates_can_overlap_without_sharing_worktrees(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, first_commit = _repository(tmp_path)
    command = (
        (
            "/bin/bash",
            "-c",
            "mkdir -p artifacts && sleep 0.5 && pwd > artifacts/gate-root.txt",
        ),
    )
    for gate in GATE_COMMANDS:
        monkeypatch.setitem(GATE_COMMANDS, gate, command)

    launches = [
        launch_frozen_gate(repository, first_commit, gate) for gate in GATE_COMMANDS
    ]

    assert len({launch.repository for launch in launches}) == len(GATE_COMMANDS)
    for launch in launches:
        assert _wait_for_status(Path(launch.status_file)) == 0
        source = Path(launch.repository)
        assert (source / "artifacts/gate-root.txt").read_text().strip() == str(source)


def test_frozen_gate_rejects_unknown_gate(tmp_path: Path) -> None:
    repository, first_commit = _repository(tmp_path)

    with pytest.raises(FrozenGateError, match="unsupported frozen gate"):
        launch_frozen_gate(repository, first_commit, "unknown")
