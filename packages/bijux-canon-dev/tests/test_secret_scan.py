from __future__ import annotations

import json
from pathlib import Path
import subprocess

from bijux_canon_dev.security.secret_scan import main, scan_repository


def _repository(tmp_path: Path, files: dict[str, bytes]) -> Path:
    repository = tmp_path / "repository"
    repository.mkdir()
    subprocess.run(("git", "init", "-q", str(repository)), check=True)
    subprocess.run(
        ("git", "-C", str(repository), "config", "user.email", "test@bijux.dev"),
        check=True,
    )
    subprocess.run(
        ("git", "-C", str(repository), "config", "user.name", "Bijux Test"),
        check=True,
    )
    for relative_path, content in files.items():
        target = repository / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    subprocess.run(("git", "-C", str(repository), "add", "--", *files), check=True)
    subprocess.run(
        ("git", "-C", str(repository), "commit", "-qm", "test fixture"), check=True
    )
    return repository


def test_scan_reports_locations_without_serializing_secret_values(tmp_path: Path) -> None:
    token = "gh" + "p_" + "a" * 36
    repository = _repository(
        tmp_path,
        {"safe.txt": b"ordinary source\n", "nested/leaked.txt": token.encode()},
    )

    report = scan_repository(repository)

    assert report["summary"]["findings"] == 1
    assert report["findings"] == [
        {"kind": "github-token", "line": 1, "path": "nested/leaked.txt"}
    ]
    assert token not in json.dumps(report)


def test_scan_ignores_untracked_files_and_records_binary_skips(tmp_path: Path) -> None:
    repository = _repository(tmp_path, {"image.bin": b"header\0payload"})
    untracked_token = "AK" + "IA" + "A" * 16
    (repository / "untracked.txt").write_text(untracked_token, encoding="utf-8")

    report = scan_repository(repository)

    assert report["summary"] == {
        "binary_files_skipped": 1,
        "findings": 0,
        "tracked_files_scanned": 1,
    }
    assert report["binary_files_skipped"] == ["image.bin"]


def test_command_writes_evidence_and_refuses_a_detected_key(
    tmp_path: Path, capsys: object
) -> None:
    del capsys
    key = "sk-" + "z" * 40
    repository = _repository(tmp_path, {"settings.txt": key.encode()})
    report = tmp_path / "evidence" / "secret-scan.json"

    assert main(["--repository", str(repository), "--output", str(report)]) == 1
    assert json.loads(report.read_text(encoding="utf-8"))["summary"]["findings"] == 1
