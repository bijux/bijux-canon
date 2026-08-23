from __future__ import annotations

import json
from pathlib import Path
import subprocess
import time

import pytest

from bijux_canon_dev.release.frozen_gate import (
    GATE_COMMANDS,
    FrozenGateError,
    FrozenGateState,
    inspect_frozen_gate,
    launch_frozen_gate,
    main,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


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
    assert source.name == repository.name
    assert source.parent == Path(launch.artifact_root)
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
    assert GATE_COMMANDS["tox"] == (
        (
            "uv",
            "tool",
            "run",
            "--from",
            "tox>=4.11,<5",
            "--with",
            "tox-gh-actions>=3.1,<4",
            "tox",
        ),
    )
    assert GATE_COMMANDS["ci-github"][0][-4:] == (
        "check-shared-bijux-py",
        "check-config-layout",
        "check-make-layout",
        "help",
    )
    assert set(GATE_COMMANDS["ci-github"]).isdisjoint(GATE_COMMANDS["tox"])


def test_frozen_gate_reports_not_started_without_scanning_artifacts(
    tmp_path: Path,
) -> None:
    repository, first_commit = _repository(tmp_path)

    status = inspect_frozen_gate(repository, first_commit, "test-all")

    assert status.state is FrozenGateState.NOT_STARTED
    assert status.exit_code is None
    assert status.started_at is None
    assert status.finished_at is None
    assert status.log_tail == ()


def test_frozen_gate_reports_completion_and_rejects_duplicate_launch(
    tmp_path: Path,
) -> None:
    repository, first_commit = _repository(tmp_path)
    launch = launch_frozen_gate(repository, first_commit, "test-all")
    assert _wait_for_status(Path(launch.status_file)) == 0

    status = inspect_frozen_gate(repository, first_commit, "test-all")

    assert status.state is FrozenGateState.PASSED
    assert status.exit_code == 0
    assert status.started_at is not None
    assert status.finished_at is not None
    with pytest.raises(FrozenGateError, match="already has a passed launch"):
        launch_frozen_gate(repository, first_commit, "test-all")


def test_frozen_gate_rejects_duplicate_active_launch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, first_commit = _repository(tmp_path)
    monkeypatch.setitem(
        GATE_COMMANDS,
        "test-all",
        (("/bin/bash", "-c", "sleep 0.5"),),
    )
    launch = launch_frozen_gate(repository, first_commit, "test-all")

    with pytest.raises(FrozenGateError, match="already has a running launch"):
        launch_frozen_gate(repository, first_commit, "test-all")

    assert _wait_for_status(Path(launch.status_file)) == 0


def test_frozen_gate_failure_summary_is_bounded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, first_commit = _repository(tmp_path)
    monkeypatch.setitem(
        GATE_COMMANDS,
        "test-all",
        (("/bin/bash", "-c", "printf 'useful failure\\n'; exit 7"),),
    )
    launch = launch_frozen_gate(repository, first_commit, "test-all")
    assert _wait_for_status(Path(launch.status_file)) == 7

    status = inspect_frozen_gate(
        repository,
        first_commit,
        "test-all",
        include_failure_tail=True,
        tail_lines=1,
    )

    assert status.state is FrozenGateState.FAILED
    assert status.exit_code == 7
    assert status.log_tail == ("useful failure",)


def test_frozen_gate_cli_has_stable_monitor_exit_semantics(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository, first_commit = _repository(tmp_path)
    arguments = [
        "--repo",
        str(repository),
        "--ref",
        first_commit,
        "--gate",
        "test-all",
    ]

    assert main([*arguments, "--action", "status"]) == 0
    assert json.loads(capsys.readouterr().out)["state"] == "not_started"
    assert main([*arguments, "--action", "summary"]) == 4
    assert json.loads(capsys.readouterr().out)["state"] == "not_started"


def test_frozen_make_targets_expose_deduplicated_monitoring_contract() -> None:
    root_make = (REPO_ROOT / "makes" / "root.mk").read_text(encoding="utf-8")

    assert "all-frozen: test-all-frozen tox-frozen ci-github-frozen" in root_make
    assert "frozen-status:" in root_make
    assert '"$(GATE)" --action status' in root_make
    assert "frozen-summary:" in root_make
    assert '"$(GATE)" --action summary' in root_make


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
