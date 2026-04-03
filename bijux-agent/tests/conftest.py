from __future__ import annotations

import builtins
from collections.abc import Generator
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import warnings

from _pytest.monkeypatch import MonkeyPatch
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ALLOWED_ARTIFACTS_ROOT = PROJECT_ROOT / "artifacts" / "test"
PYCACHE_PREFIX = ALLOWED_ARTIFACTS_ROOT / "pycache"
PYCACHE_PREFIX.mkdir(parents=True, exist_ok=True)
sys.dont_write_bytecode = True
sys.pycache_prefix = str(PYCACHE_PREFIX)
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
os.environ.setdefault("PYTHONPYCACHEPREFIX", str(PYCACHE_PREFIX))
os.environ.setdefault("COVERAGE_FILE", str(ALLOWED_ARTIFACTS_ROOT / ".coverage"))
EXEMPT_PATH_SEGMENTS = {
    ".venv",
    ".pytest_cache",
    ".hypothesis",
    "site-packages",
    "__pycache__",
}

from bijux_agent.utilities.logger_manager import (  # noqa: E402
    LoggerConfig,
    LoggerManager,
)

# TODO(pydantic-v3): migrate to ConfigDict/field_validator fully and remove this filter.
warnings.filterwarnings(
    "ignore",
    message=r".*Pydantic" + "Depre" + "catedSince20.*",
)


def _assert_within_allowed(path: Path) -> None:
    resolved = path.resolve()
    if resolved == ALLOWED_ARTIFACTS_ROOT or ALLOWED_ARTIFACTS_ROOT in resolved.parents:
        return
    if any(segment in resolved.parts for segment in EXEMPT_PATH_SEGMENTS):
        return
    raise RuntimeError(
        "Writes, temporary files, and artifacts must stay under 'artifacts/test/'"
    )


@pytest.fixture(scope="session", autouse=True)
def enforce_artifact_boundary():
    ALLOWED_ARTIFACTS_ROOT.mkdir(parents=True, exist_ok=True)

    mp = MonkeyPatch()
    mp.setattr(Path, "cwd", classmethod(lambda cls: ALLOWED_ARTIFACTS_ROOT))
    mp.setattr(tempfile, "gettempdir", lambda: str(ALLOWED_ARTIFACTS_ROOT))

    original_mkdir = Path.mkdir
    original_open = Path.open
    original_write_text = Path.write_text
    original_write_bytes = Path.write_bytes
    original_open_builtin = builtins.open
    original_os_mkdir = os.mkdir
    original_os_makedirs = os.makedirs

    def guarded_mkdir(self, *args, **kwargs):
        _assert_within_allowed(self)
        return original_mkdir(self, *args, **kwargs)

    def guarded_write_text(self, *args, **kwargs):
        _assert_within_allowed(self)
        return original_write_text(self, *args, **kwargs)

    def guarded_write_bytes(self, *args, **kwargs):
        _assert_within_allowed(self)
        return original_write_bytes(self, *args, **kwargs)

    def guarded_path_open(self, *args, **kwargs):
        mode = kwargs.get("mode", args[0] if args else "r")
        if any(token in mode for token in ("w", "a", "x", "+")):
            _assert_within_allowed(self)
        return original_open(self, *args, **kwargs)

    def guarded_builtin_open(file, *args, **kwargs):
        mode = kwargs.get("mode", args[0] if args else "r")
        if isinstance(file, (str, Path, bytes)) and any(
            token in mode for token in ("w", "a", "x", "+")
        ):
            _assert_within_allowed(Path(file))
        return original_open_builtin(file, *args, **kwargs)

    mp.setattr(Path, "mkdir", guarded_mkdir, raising=False)
    mp.setattr(Path, "write_text", guarded_write_text, raising=False)
    mp.setattr(Path, "write_bytes", guarded_write_bytes, raising=False)
    mp.setattr(Path, "open", guarded_path_open, raising=False)
    mp.setattr(builtins, "open", guarded_builtin_open, raising=False)
    mp.setattr(
        os,
        "mkdir",
        lambda path, *args, **kwargs: _assert_within_allowed(Path(path))
        or original_os_mkdir(path, *args, **kwargs),
        raising=False,
    )
    mp.setattr(
        os,
        "makedirs",
        lambda path, *args, **kwargs: _assert_within_allowed(Path(path))
        or original_os_makedirs(path, *args, **kwargs),
        raising=False,
    )

    yield

    mp.undo()


def _git_untracked(root: Path) -> set[str]:
    completed = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
        cwd=root,
        check=True,
    )
    entries = set()
    for line in completed.stdout.splitlines():
        status = line[:2]
        path = line[3:]
        if status.strip() == "??":
            entries.add(path.strip())
    return entries


def _relocate_coverage_files() -> None:
    for coverage_path in PROJECT_ROOT.glob(".coverage*"):
        if ALLOWED_ARTIFACTS_ROOT in coverage_path.parents:
            continue
        destination = ALLOWED_ARTIFACTS_ROOT / coverage_path.name
        coverage_path.rename(destination)


@pytest.fixture(scope="session", autouse=True)
def enforce_git_clean() -> Generator[None, None, None]:
    before = _git_untracked(PROJECT_ROOT)
    yield
    _relocate_coverage_files()
    after = _git_untracked(PROJECT_ROOT)
    new = after - before
    disallowed = [path for path in new if not path.startswith("artifacts/test/")]
    if disallowed:
        pytest.fail(
            "Untracked paths appeared outside artifacts/test/: " + ", ".join(disallowed)
        )


@pytest.fixture
def test_artifacts_dir(request) -> Path:
    safe_name = (
        request.node.nodeid.replace("::", "__").replace("/", "_").replace("\\", "_")
    )
    target = ALLOWED_ARTIFACTS_ROOT / safe_name
    target.mkdir(parents=True, exist_ok=True)
    return target


@pytest.fixture
def tmp_path(test_artifacts_dir: Path) -> Path:
    return test_artifacts_dir


@pytest.fixture
def logger_manager(tmp_path: Path) -> LoggerManager:
    return LoggerManager(LoggerConfig(log_dir=tmp_path / "logs"))
