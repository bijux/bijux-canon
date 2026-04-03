from __future__ import annotations

import subprocess
from pathlib import Path


def package_root() -> Path:
    return Path(__file__).resolve().parents[6] / "packages" / "bijux-canon-agent"


def main() -> int:
    result = subprocess.run(
        ["git", "ls-files", "--others", "--directory", "--exclude-standard"],
        capture_output=True,
        text=True,
        check=False,
        cwd=package_root(),
    )
    offenders = sorted(path for path in result.stdout.splitlines() if path.endswith("/"))
    if offenders:
        print("error: unexpected untracked directories found:")
        for path in offenders:
            print(f"  - {path}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
