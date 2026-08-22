"""Launch repository gates against isolated tracked revisions."""

from __future__ import annotations

import argparse
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import fcntl
import json
import os
from pathlib import Path
import shlex
import subprocess


class FrozenGateError(RuntimeError):
    """A frozen gate could not be prepared or launched safely."""


TOX_COMMAND = (
    "uv",
    "tool",
    "run",
    "--from",
    "tox>=4.11,<5",
    "--with",
    "tox-gh-actions>=3.1,<4",
    "tox",
)

GATE_COMMANDS: dict[str, tuple[tuple[str, ...], ...]] = {
    "test-all": (("make", "--no-print-directory", "test-all"),),
    "tox": (TOX_COMMAND,),
    "ci-github": (
        (
            "make",
            "--no-print-directory",
            "check-shared-bijux-py",
            "check-config-layout",
            "check-make-layout",
            "help",
        ),
        TOX_COMMAND,
    ),
}


@dataclass(frozen=True)
class FrozenGateLaunch:
    """Paths and identities for one detached frozen gate process."""

    artifact_root: str
    commit: str
    commit_count: int
    console_log: str
    gate: str
    metadata_file: str
    pid: int
    repository: str
    status_file: str


def _run(
    command: Sequence[str],
    *,
    cwd: Path,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        tuple(command),
        cwd=cwd,
        capture_output=True,
        check=False,
        text=True,
    )
    if check and completed.returncode != 0:
        raise FrozenGateError(f"{' '.join(command)} failed: {completed.stderr.strip()}")
    return completed


def _git_text(repository: Path, *arguments: str) -> str:
    return _run(
        ("git", "-C", str(repository), *arguments), cwd=repository
    ).stdout.strip()


def _pid_is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        completed_pid, _ = os.waitpid(pid, os.WNOHANG)
    except ChildProcessError:
        pass
    else:
        if completed_pid == pid:
            return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


@contextmanager
def _launch_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _validate_repository(repository: Path) -> Path:
    repository = repository.resolve()
    if not repository.is_dir():
        raise FrozenGateError(f"repository does not exist: {repository}")
    top_level = Path(_git_text(repository, "rev-parse", "--show-toplevel")).resolve()
    if top_level != repository:
        raise FrozenGateError(
            f"repository must be its Git top level: {repository} != {top_level}"
        )
    return repository


def _prepare_clone(repository: Path, source: Path, commit: str) -> None:
    if not source.exists():
        source.parent.mkdir(parents=True, exist_ok=True)
        _run(
            (
                "git",
                "clone",
                "--no-local",
                "--no-checkout",
                "--quiet",
                str(repository),
                str(source),
            ),
            cwd=repository,
        )
        _run(
            ("git", "checkout", "--detach", "--force", commit),
            cwd=source,
        )

    observed = _git_text(source, "rev-parse", "HEAD")
    if observed != commit:
        raise FrozenGateError(
            f"frozen source commit mismatch: expected {commit}, observed {observed}"
        )
    if _run(("git", "diff", "--quiet"), cwd=source, check=False).returncode != 0:
        raise FrozenGateError(f"frozen source has tracked changes: {source}")
    if (
        _run(("git", "diff", "--cached", "--quiet"), cwd=source, check=False).returncode
        != 0
    ):
        raise FrozenGateError(f"frozen source has staged changes: {source}")
    unexpected = [
        path
        for path in _git_text(
            source, "ls-files", "--others", "--exclude-standard"
        ).splitlines()
        if path and not path.startswith("artifacts/")
    ]
    if unexpected:
        raise FrozenGateError(
            f"frozen source has unexpected untracked content: {unexpected[0]}"
        )


def _launcher_script(
    *,
    source: Path,
    commands: Sequence[Sequence[str]],
    status_file: Path,
) -> str:
    artifact_root = source / "artifacts"
    exports = {
        "HYPOTHESIS_STORAGE_DIRECTORY": artifact_root / "root/hypothesis",
        "NPM_CONFIG_CACHE": artifact_root / "root/npm-cache",
        "PIP_CACHE_DIR": artifact_root / "root/pip-cache",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPYCACHEPREFIX": artifact_root / "root/pycache",
        "TMPDIR": artifact_root / "root/process",
        "TOX_WORK_DIR": artifact_root / "root/tox",
        "UV_CACHE_DIR": artifact_root / "root/uv-cache",
        "XDG_CACHE_HOME": artifact_root / "root/xdg-cache",
    }
    lines = [
        "#!/bin/bash",
        "set -u -o pipefail",
        f"cd {shlex.quote(str(source))}",
        "unset MAKEFLAGS MFLAGS PYTHONPATH UV_PROJECT_ENVIRONMENT VIRTUAL_ENV",
    ]
    lines.extend(
        f"export {name}={shlex.quote(str(value))}" for name, value in exports.items()
    )
    lines.extend(
        (
            f"mkdir -p {shlex.quote(str(artifact_root / 'root/process'))}",
            "status=0",
            "set +e",
        )
    )
    for command in commands:
        lines.extend(
            (
                'if [[ "${status}" -eq 0 ]]; then',
                f"  {shlex.join(command)}",
                "  status=$?",
                "fi",
            )
        )
    lines.extend(
        (
            "set -e",
            f"printf '%s\\n' \"${{status}}\" > {shlex.quote(str(status_file))}",
            'exit "${status}"',
            "",
        )
    )
    return "\n".join(lines)


def launch_frozen_gate(
    repository: Path,
    revision: str,
    gate: str,
) -> FrozenGateLaunch:
    """Launch ``gate`` against ``revision`` without touching the live checkout."""
    repository = _validate_repository(repository)
    try:
        commands = GATE_COMMANDS[gate]
    except KeyError as exc:
        raise FrozenGateError(f"unsupported frozen gate: {gate}") from exc
    commit = _git_text(
        repository,
        "rev-parse",
        "--verify",
        "--end-of-options",
        f"{revision}^{{commit}}",
    )
    commit_count = int(_git_text(repository, "rev-list", "--count", commit))
    identity = f"{commit_count}-{commit[:8]}"
    artifact_root = repository / "artifacts" / "frozen" / identity / gate
    # Workspace-aware Make gates resolve the current repository by its slug
    # beneath the checkout parent, so preserve that shape in every frozen run.
    source = artifact_root / repository.name
    console_log = artifact_root / "console.log"
    metadata_file = artifact_root / "launch.json"
    pid_file = artifact_root / "process.pid"
    status_file = artifact_root / "exit.status"
    launcher = artifact_root / "launch.sh"

    with _launch_lock(artifact_root / "launch.lock"):
        if pid_file.is_file():
            try:
                existing_pid = int(pid_file.read_text(encoding="utf-8").strip())
            except ValueError:
                existing_pid = 0
            if _pid_is_running(existing_pid):
                raise FrozenGateError(
                    f"{gate} is already running for {identity}: pid {existing_pid}"
                )

        _prepare_clone(repository, source, commit)
        status_file.unlink(missing_ok=True)
        launcher.write_text(
            _launcher_script(
                source=source,
                commands=commands,
                status_file=status_file,
            ),
            encoding="utf-8",
        )
        launcher.chmod(0o755)
        with console_log.open("wb", buffering=0) as console:
            process = subprocess.Popen(
                ("/bin/bash", str(launcher)),
                stdin=subprocess.DEVNULL,
                stdout=console,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                close_fds=True,
            )
        launch = FrozenGateLaunch(
            artifact_root=str(artifact_root),
            commit=commit,
            commit_count=commit_count,
            console_log=str(console_log),
            gate=gate,
            metadata_file=str(metadata_file),
            pid=process.pid,
            repository=str(source),
            status_file=str(status_file),
        )
        pid_file.write_text(f"{process.pid}\n", encoding="utf-8")
        metadata = {
            **asdict(launch),
            "commands": [list(command) for command in commands],
            "requested_revision": revision,
            "schema_version": "bijux.canon.frozen_gate_launch.v1",
            "started_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        }
        metadata_file.write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return launch


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Launch a repository gate from an isolated tracked revision."
    )
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--gate", choices=sorted(GATE_COMMANDS), required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the frozen gate launcher."""
    parser = _parser()
    arguments = parser.parse_args(argv)
    try:
        launch = launch_frozen_gate(arguments.repo, arguments.ref, arguments.gate)
    except FrozenGateError as exc:
        parser.error(str(exc))
    print(f"started {launch.gate} for {launch.commit_count}-{launch.commit[:8]}")
    print(f"source: {launch.repository}")
    print(f"artifacts: {launch.artifact_root}")
    print(f"console: {launch.console_log}")
    print(f"status: {launch.status_file}")
    print(f"pid: {launch.pid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
