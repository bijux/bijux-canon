from __future__ import annotations

from pathlib import Path
import shutil

from bijux_canon_dev.trusted_process import run_text


def package_root() -> Path:
    return Path(__file__).resolve().parents[6] / "packages" / "bijux-canon-agent"


def git_executable() -> str:
    resolved = shutil.which("git")
    if resolved is None:
        raise SystemExit("git executable not found")
    return resolved


def main() -> int:
    result = run_text(
        [
            git_executable(),
            "ls-files",
            "--others",
            "--directory",
            "--exclude-standard",
        ],
        capture_output=True,
        check=False,
        cwd=package_root(),
    )
    offenders = sorted(
        path for path in result.stdout.splitlines() if path.endswith("/")
    )
    if offenders:
        print("error: unexpected untracked directories found:")
        for path in offenders:
            print(f"  - {path}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
