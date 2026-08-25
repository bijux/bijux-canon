"""Launch repository gates against isolated tracked revisions."""

from __future__ import annotations

import argparse
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
import fcntl
import json
import os
from pathlib import Path
import shlex
import subprocess


class FrozenGateError(RuntimeError):
    """A frozen gate could not be prepared or launched safely."""


@dataclass(frozen=True)
class GateResponsibility:
    """One non-overlapping release responsibility and its exact command."""

    command: tuple[str, ...]
    covers: tuple[str, ...]
    responsibility_id: str


REQUIRED_RESPONSIBILITIES = frozenset(
    {
        "api",
        "builds",
        "docs",
        "product-acceptance",
        "quality",
        "real-wheels",
        "sbom",
        "security",
        "tests",
        "typing",
    }
)

CANDIDATE_RESPONSIBILITIES = (
    GateResponsibility(
        command=("make", "--no-print-directory", "test-all"),
        covers=("tests", "product-acceptance"),
        responsibility_id="tests-and-product-acceptance",
    ),
    GateResponsibility(
        command=("make", "--no-print-directory", "quality"),
        covers=("quality", "typing"),
        responsibility_id="quality-and-typing",
    ),
    GateResponsibility(
        command=("make", "--no-print-directory", "security"),
        covers=("security",),
        responsibility_id="security",
    ),
    GateResponsibility(
        command=("make", "--no-print-directory", "docs", "api"),
        covers=("docs", "api"),
        responsibility_id="docs-and-api",
    ),
    GateResponsibility(
        command=("make", "--no-print-directory", "build", "sbom"),
        covers=("builds", "real-wheels", "sbom"),
        responsibility_id="builds-real-wheels-and-sbom",
    ),
)

GATE_RESPONSIBILITIES: dict[str, tuple[GateResponsibility, ...]] = {
    "candidate": CANDIDATE_RESPONSIBILITIES,
}
GATE_COMMANDS: dict[str, tuple[tuple[str, ...], ...]] = {
    gate: tuple(item.command for item in responsibilities)
    for gate, responsibilities in GATE_RESPONSIBILITIES.items()
}


class FrozenGateState(StrEnum):
    """Stable lifecycle states exposed by frozen-gate monitoring."""

    NOT_STARTED = "not_started"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    STALE = "stale"


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


@dataclass(frozen=True)
class FrozenGateStatus:
    """Concise status for one commit and gate identity."""

    artifact_root: str
    commit: str
    commit_count: int
    console_log: str
    exit_code: int | None
    finished_at: str | None
    gate: str
    log_tail: tuple[str, ...]
    metadata_file: str
    pid: int | None
    repository: str
    started_at: str | None
    state: FrozenGateState
    status_file: str

    def record(self) -> dict[str, object]:
        """Return the stable JSON-compatible monitoring record."""
        return asdict(self)


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


def _resolved_identity(repository: Path, revision: str) -> tuple[str, int, str]:
    commit = _git_text(
        repository,
        "rev-parse",
        "--verify",
        "--end-of-options",
        f"{revision}^{{commit}}",
    )
    commit_count = int(_git_text(repository, "rev-list", "--count", commit))
    return commit, commit_count, f"{commit_count}-{commit[:8]}"


def _require_gate(gate: str) -> tuple[tuple[str, ...], ...]:
    try:
        return GATE_COMMANDS[gate]
    except KeyError as exc:
        raise FrozenGateError(f"unsupported frozen gate: {gate}") from exc


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


def _timestamp(path: Path) -> str:
    return (
        datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _bounded_log_tail(path: Path, *, line_count: int) -> tuple[str, ...]:
    if line_count < 1 or not path.is_file():
        return ()
    byte_limit = 64 * 1024
    with path.open("rb") as stream:
        stream.seek(0, os.SEEK_END)
        size = stream.tell()
        stream.seek(max(0, size - byte_limit))
        payload = stream.read(byte_limit)
    text = payload.decode("utf-8", errors="replace")
    lines = text.splitlines()
    return tuple(lines[-line_count:])


def inspect_frozen_gate(
    repository: Path,
    revision: str,
    gate: str,
    *,
    include_failure_tail: bool = False,
    tail_lines: int = 20,
) -> FrozenGateStatus:
    """Inspect one exact gate identity without scanning frozen artifacts."""
    repository = _validate_repository(repository)
    _require_gate(gate)
    commit, commit_count, identity = _resolved_identity(repository, revision)
    artifact_root = repository / "artifacts" / "frozen" / identity / gate
    source = artifact_root / repository.name
    console_log = artifact_root / "console.log"
    metadata_file = artifact_root / "launch.json"
    status_file = artifact_root / "exit.status"
    if not metadata_file.is_file():
        return FrozenGateStatus(
            artifact_root=str(artifact_root),
            commit=commit,
            commit_count=commit_count,
            console_log=str(console_log),
            exit_code=None,
            finished_at=None,
            gate=gate,
            log_tail=(),
            metadata_file=str(metadata_file),
            pid=None,
            repository=str(source),
            started_at=None,
            state=FrozenGateState.NOT_STARTED,
            status_file=str(status_file),
        )
    try:
        metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
        pid = int(metadata["pid"])
        started_at = str(metadata["started_at"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise FrozenGateError(
            f"frozen gate metadata is invalid: {metadata_file}"
        ) from exc
    if metadata.get("commit") != commit or metadata.get("gate") != gate:
        raise FrozenGateError(
            f"frozen gate metadata identity mismatch: {metadata_file}"
        )
    exit_code: int | None = None
    finished_at: str | None = None
    if status_file.is_file():
        try:
            exit_code = int(status_file.read_text(encoding="utf-8").strip())
        except ValueError as exc:
            raise FrozenGateError(
                f"frozen gate exit status is invalid: {status_file}"
            ) from exc
        finished_at = _timestamp(status_file)
        state = FrozenGateState.PASSED if exit_code == 0 else FrozenGateState.FAILED
    elif _pid_is_running(pid):
        state = FrozenGateState.RUNNING
    else:
        state = FrozenGateState.STALE
    log_tail = (
        _bounded_log_tail(console_log, line_count=tail_lines)
        if include_failure_tail
        and state in {FrozenGateState.FAILED, FrozenGateState.STALE}
        else ()
    )
    return FrozenGateStatus(
        artifact_root=str(artifact_root),
        commit=commit,
        commit_count=commit_count,
        console_log=str(console_log),
        exit_code=exit_code,
        finished_at=finished_at,
        gate=gate,
        log_tail=log_tail,
        metadata_file=str(metadata_file),
        pid=pid,
        repository=str(source),
        started_at=started_at,
        state=state,
        status_file=str(status_file),
    )


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
    commands = _require_gate(gate)
    commit, commit_count, identity = _resolved_identity(repository, revision)
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
        if metadata_file.is_file():
            existing = inspect_frozen_gate(repository, commit, gate)
            detail = (
                f": pid {existing.pid}"
                if existing.state is FrozenGateState.RUNNING
                else ""
            )
            raise FrozenGateError(
                f"{gate} already has a {existing.state.value} launch "
                f"for {identity}{detail}"
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
            "responsibility_graph": [
                asdict(item) for item in GATE_RESPONSIBILITIES[gate]
            ],
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
        description="Launch or inspect a gate against an isolated tracked revision."
    )
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--gate", choices=sorted(GATE_COMMANDS), required=True)
    parser.add_argument(
        "--action",
        choices=("launch", "status", "summary"),
        default="launch",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the frozen gate launcher."""
    parser = _parser()
    arguments = parser.parse_args(argv)
    try:
        if arguments.action in {"status", "summary"}:
            status = inspect_frozen_gate(
                arguments.repo,
                arguments.ref,
                arguments.gate,
                include_failure_tail=arguments.action == "summary",
            )
            print(json.dumps(status.record(), sort_keys=True))
            if arguments.action == "status":
                return 0
            return {
                FrozenGateState.PASSED: 0,
                FrozenGateState.FAILED: 1,
                FrozenGateState.RUNNING: 3,
                FrozenGateState.NOT_STARTED: 4,
                FrozenGateState.STALE: 5,
            }[status.state]
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
