"""Protect the documentation-only install boundary and other local environments."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from bijux_canon_dev.docs import environment

ROOT = Path(__file__).resolve().parents[3]


class DocumentationEnvironmentTests(unittest.TestCase):
    def setUp(self) -> None:
        parent = ROOT / "artifacts/website-security/docs-environment-controls"
        parent.mkdir(parents=True, exist_ok=True)
        self.sandbox = tempfile.TemporaryDirectory(dir=parent)
        self.addCleanup(self.sandbox.cleanup)
        self.root = Path(self.sandbox.name)
        self.other = self.root / "artifacts/root/check-venv/user-input"
        self.other.parent.mkdir(parents=True)
        self.other.write_text("preserve unrelated development environment\n")
        self.addCleanup(self.assert_other_preserved)

    def assert_other_preserved(self) -> None:
        self.assertEqual(
            self.other.read_text(), "preserve unrelated development environment\n"
        )

    def own(self) -> Path:
        selected = self.root / environment.ENVIRONMENT
        selected.mkdir(parents=True)
        (selected / ".ownership.json").write_text(json.dumps(environment.OWNERSHIP))
        return selected

    def test_each_symlinked_environment_ancestor_rejects_before_mutation(self) -> None:
        for relative in [
            "artifacts",
            "artifacts/root",
            "artifacts/root/docs",
            environment.ENVIRONMENT,
        ]:
            with self.subTest(relative=relative):
                root = self.root / ("symlink-" + relative.replace("/", "-"))
                root.mkdir()
                target = root / "preserve"
                target.mkdir()
                link = root / relative
                link.parent.mkdir(parents=True, exist_ok=True)
                link.symlink_to(target, target_is_directory=True)
                with patch.object(subprocess, "run") as command:
                    with self.assertRaisesRegex(ValueError, "symlinks"):
                        environment.install(root, sys.executable, "uv")
                    command.assert_not_called()
                self.assertEqual(list(target.iterdir()), [])

    def test_symlinked_process_or_cache_rejects_before_external_write(self) -> None:
        for name in ("uv-cache", "process"):
            with self.subTest(name=name):
                root = self.root / name
                root.mkdir()
                external = root / "external"
                external.mkdir()
                link = root / ("artifacts/root/docs/" + name)
                link.parent.mkdir(parents=True)
                link.symlink_to(external, target_is_directory=True)
                with patch.object(subprocess, "run") as command:
                    with self.assertRaisesRegex(ValueError, "process/cache"):
                        environment.install(root, sys.executable, "uv")
                    command.assert_not_called()
                self.assertEqual(list(external.iterdir()), [])
                self.assertFalse((root / environment.ENVIRONMENT).exists())

    def test_unowned_existing_environment_is_preserved(self) -> None:
        selected = self.root / environment.ENVIRONMENT
        selected.mkdir(parents=True)
        marker = selected / "user-file"
        marker.write_text("preserve existing bytes")
        with patch.object(subprocess, "run") as command:
            with self.assertRaisesRegex(ValueError, "unowned"):
                environment.install(self.root, sys.executable, "uv")
            command.assert_not_called()
        self.assertEqual(marker.read_text(), "preserve existing bytes")

    def test_wrong_or_malformed_ownership_never_admits_environment(self) -> None:
        selected = self.own()
        for content in [
            "not JSON",
            "{}",
            "[]",
            '{"schema": 9}',
            json.dumps({**environment.OWNERSHIP, "purpose": "other"}),
        ]:
            with self.subTest(content=content):
                marker = selected / ".ownership.json"
                marker.write_text(content)
                with patch.object(subprocess, "run") as command:
                    with self.assertRaises(ValueError):
                        environment.install(self.root, sys.executable, "uv")
                    command.assert_not_called()
                self.assertEqual(marker.read_text(), content)

    def test_symlinked_ownership_rejects_without_following_it(self) -> None:
        selected = self.own()
        marker = selected / ".ownership.json"
        marker.unlink()
        external = self.root / "foreign-marker"
        external.write_text(json.dumps(environment.OWNERSHIP))
        marker.symlink_to(external)
        with patch.object(subprocess, "run") as command:
            with self.assertRaisesRegex(ValueError, "unowned"):
                environment.install(self.root, sys.executable, "uv")
            command.assert_not_called()
        self.assertTrue(marker.is_symlink())

    def test_environment_file_rejects_without_replacement(self) -> None:
        selected = self.root / environment.ENVIRONMENT
        selected.parent.mkdir(parents=True)
        selected.write_text("preserve file")
        with self.assertRaisesRegex(ValueError, "directory"):
            environment.install(self.root, sys.executable, "uv")
        self.assertEqual(selected.read_text(), "preserve file")

    def test_fresh_install_uses_stdlib_without_pip_and_excludes_workspace(self) -> None:
        calls = []
        with patch.object(
            subprocess,
            "run",
            lambda args, **kwargs: calls.append((args, kwargs)),
        ):
            environment.install(self.root, sys.executable, "uv")
        self.assertEqual(len(calls), 2)
        self.assertIn("--without-pip", calls[0][0])
        self.assertIn("--locked", calls[1][0])
        self.assertIn("--no-install-workspace", calls[1][0])
        self.assertEqual(calls[1][0][calls[1][0].index("--only-group") + 1], "docs")
        self.assertNotIn("dev", calls[1][0])
        for _, kwargs in calls:
            self.assertEqual(
                kwargs["env"]["UV_PROJECT_ENVIRONMENT"],
                str(self.root / environment.ENVIRONMENT),
            )
            self.assertEqual(kwargs["env"]["UV_PYTHON_DOWNLOADS"], "never")
            self.assertEqual(
                kwargs["env"]["UV_CACHE_DIR"],
                str(self.root / "artifacts/root/docs/uv-cache"),
            )

    def test_existing_owned_interpreter_resumes_sync_without_recreation(self) -> None:
        selected = self.own()
        executable = selected / "bin/python"
        executable.parent.mkdir()
        executable.write_text("existing controlled interpreter")
        with patch.object(subprocess, "run") as command:
            environment.install(self.root, sys.executable, "uv")
        self.assertEqual(command.call_count, 1)
        self.assertEqual(command.call_args.args[0][1], "sync")
        self.assertEqual(executable.read_text(), "existing controlled interpreter")

    def test_interrupted_owned_creation_can_resume_without_reset(self) -> None:
        with (
            patch.object(
                subprocess,
                "run",
                side_effect=subprocess.CalledProcessError(1, ["python", "-m", "venv"]),
            ),
            self.assertRaises(subprocess.CalledProcessError),
        ):
            environment.install(self.root, sys.executable, "uv")
        selected = self.root / environment.ENVIRONMENT
        self.assertEqual(
            json.loads((selected / ".ownership.json").read_text()),
            environment.OWNERSHIP,
        )
        preserved = selected / "partial-output"
        preserved.write_text("retain interrupted evidence")
        with patch.object(subprocess, "run") as command:
            environment.install(self.root, sys.executable, "uv")
        self.assertEqual(command.call_count, 2)
        self.assertEqual(preserved.read_text(), "retain interrupted evidence")


if __name__ == "__main__":
    unittest.main()
