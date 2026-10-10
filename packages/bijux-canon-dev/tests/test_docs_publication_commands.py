"""Exercise Canon's production command boundary without publishing a site."""

from __future__ import annotations

from contextlib import AbstractContextManager
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from bijux_canon_dev.docs import publication

ROOT = Path(__file__).resolve().parents[3]


class DocumentationPublicationCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.artifacts = ROOT / "artifacts/website-security/command-contracts"
        self.artifacts.mkdir(parents=True, exist_ok=True)
        self.sandbox = tempfile.TemporaryDirectory(
            prefix="publication-input-", dir=self.artifacts
        )
        self.addCleanup(self.sandbox.cleanup)
        self.root = Path(self.sandbox.name)
        self.observations: list[dict[str, object]] = []
        self.proof = self.artifacts / "proofs" / self._testMethodName
        self.proof.mkdir(parents=True, exist_ok=True)
        self.addCleanup(self.retain)
        self.environment = dict(os.environ)
        for name in (
            "GITHUB_SHA",
            "BIJUX_STD_LOCAL_VERIFY",
            "BIJUX_STD_ALLOW_LOCAL_SOURCE",
            "DOCS_BUILD_SITE_URL",
            "DOCS_SITE_DIR",
            "DOCS_PUBLICATION_SITE_URL",
            "DOCS_PUBLICATION_SITE_DIR",
        ):
            self.environment.pop(name, None)
        self.bytecode_patch = patch.object(sys, "dont_write_bytecode", True)
        self.bytecode_patch.start()
        self.addCleanup(self.bytecode_patch.stop)
        self.environment_patch = patch.dict(os.environ, self.environment, clear=True)
        self.environment_patch.start()
        self.addCleanup(self.environment_patch.stop)
        self.makefile = self.root / "Makefile"
        self.makefile.write_text(
            "DOCS_PUBLICATION_PYTHON := "
            + sys.executable
            + '\nCANON_DEV_PYTHON_ENV := PYTHONPATH="'
            + str(ROOT / "packages/bijux-canon-dev/src")
            + '"\n'
            "DOCS_BUILD_SITE_URL := http://127.0.0.1:8001/\nDOCS_SITE_DIR := artifacts/docs/site\n"
            "include " + str(ROOT / "makes/docs-publication.mk") + "\n"
            "root-check-env:\n\t@mkdir -p artifacts; touch artifacts/install-interface-reached\n"
        )
        self.public = self.root / publication.SITE_DIR
        self.public.mkdir(parents=True)
        (self.public / "index.html").write_text("Preserve original public bytes\n")
        self.addCleanup(self.assert_public_preserved)

    def assert_public_preserved(self) -> None:
        self.assertEqual(
            (self.public / "index.html").read_text(), "Preserve original public bytes\n"
        )

    def retain(self) -> None:
        (self.proof / "observations.json").write_text(
            json.dumps(self.observations, indent=2) + "\n"
        )

    def make(
        self, target: str, *assignments: str, dry: bool = False
    ) -> subprocess.CompletedProcess[str]:
        command = [
            "make",
            "--no-print-directory",
            *(["-n"] if dry else []),
            target,
            *assignments,
        ]
        result = subprocess.run(
            command, cwd=self.root, env=self.environment, text=True, capture_output=True
        )
        self.observations.append(
            {
                "kind": "actual-Make-command",
                "command": command,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        )
        return result

    def source(self) -> None:
        identity_source = ROOT / ".bijux/shared/bijux-docs/security/build_identity.py"
        identity = self.root / ".bijux/shared/bijux-docs/security/build_identity.py"
        identity.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(identity_source, identity)
        pin = self.root / ".github/standards/bijux-std.sha"
        pin.parent.mkdir(parents=True, exist_ok=True)
        pin.write_text("a" * 40 + "\n")
        (self.root / "mkdocs.yml").write_text(
            "site_name: Controlled command interface\n"
        )
        (self.root / ".gitignore").write_text("artifacts/\n")
        for arguments in [
            ["init", "-q"],
            ["config", "user.email", "bijux@example.invalid"],
            ["config", "user.name", "Bijux command tests"],
            ["add", "Makefile", ".bijux", ".github", "mkdocs.yml", ".gitignore"],
            ["commit", "-qm", "test(docs): define controlled command source"],
        ]:
            subprocess.run(
                ["git", *arguments], cwd=self.root, check=True, capture_output=True
            )

    def test_wrong_production_urls_fail_real_build_and_verify_before_mutation(
        self,
    ) -> None:
        for target in ("gh-docs-build", "gh-docs-verify"):
            for value in (
                "http://127.0.0.1:8000/",
                "https://bijux.io/",
                "http://bijux.io/bijux-canon/",
                "https://bijux.io/bijux-canon",
            ):
                with self.subTest(target=target, value=value):
                    result = self.make(target, "DOCS_BUILD_SITE_URL=" + value)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("requires exact production URL", result.stderr)
                    self.assertFalse((self.root / publication.STANDARD_ROOT).exists())

    def test_wrong_artifacts_fail_real_build_and_verify_before_mutation(self) -> None:
        for target in ("gh-docs-build", "gh-docs-verify"):
            for value in (
                "artifacts/docs/site",
                "site",
                "/absolute/site",
                "artifacts/root/docs/../build-site",
            ):
                with self.subTest(target=target, value=value):
                    result = self.make(target, "DOCS_SITE_DIR=" + value)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("requires exact artifact", result.stderr)
                    self.assertFalse((self.root / publication.STANDARD_ROOT).exists())

    def test_development_file_defaults_do_not_replace_production_identity(self) -> None:
        result = self.make("gh-docs-build", dry=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--site-url "' + publication.SITE_URL + '"', result.stdout)
        self.assertIn('--site-dir "' + publication.SITE_DIR + '"', result.stdout)
        self.assertNotIn('--site-url "http://127.0.0.1', result.stdout)

    def test_local_authority_bypass_is_rejected(self) -> None:
        self.environment["BIJUX_STD_LOCAL_VERIFY"] = "1"
        result = self.make("gh-docs-build")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cannot use local candidate authority", result.stderr)

    def test_install_command_selects_documentation_environment_without_root_dev(
        self,
    ) -> None:
        result = self.make(
            "gh-docs-install", "PYTHON=" + sys.executable, "UV=uv", dry=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("bijux_canon_dev.docs.environment", result.stdout)
        self.assertNotIn("install-interface-reached", result.stdout)
        self.assertFalse((self.root / "artifacts/install-interface-reached").exists())

    def test_dirty_source_rejects_real_make_before_standard_fetch_or_public_mutation(
        self,
    ) -> None:
        self.source()
        (self.root / "mkdocs.yml").write_text("Changed unreviewed source\n")
        result = self.make("gh-docs-build")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source is dirty", result.stderr)
        self.assertFalse((self.root / publication.STANDARD_ROOT).exists())

    def test_build_protocol_binds_receipts_and_does_not_invent_approval(self) -> None:
        self.source()
        calls: list[tuple[str, tuple[str, ...]]] = []

        def accepted(root: Path, pin: str) -> str:
            calls.append(("standard", (pin,)))
            return publication.STANDARD_ROOT + "/" + pin

        with (
            patch.object(publication, "accepted_standard", accepted),
            patch.object(
                publication,
                "command",
                lambda root, *args, **kwargs: calls.append(("command", args)),
            ),
        ):
            publication.build(self.root)
        self.observations.append(
            {
                "kind": "controlled-command-interface-only",
                "calls": calls,
                "publication_approval": False,
            }
        )
        commands = [args for kind, args in calls if kind == "command"]
        self.assertEqual(len(commands), 5)
        self.assertEqual(commands[0][:2], ("bash", "-c"))
        self.assertIn("verify_docs_authority", commands[0][2])
        self.assertIn("project_bijux_docs.py", commands[0][2])
        self.assertIn("--check", commands[0][2])
        self.assertEqual(commands[0][-1], sys.executable)
        self.assertIn("capture-source", commands[1])
        self.assertEqual(
            commands[1][commands[1].index("--standard-root") + 1],
            publication.STANDARD_ROOT + "/" + "a" * 40,
        )
        self.assertIn("--source-identity", commands[2])
        self.assertTrue(commands[2][1].endswith("render_publication.py"))
        self.assertIn("admit", commands[3])
        self.assertIn("--csp-report", commands[3])
        self.assertIn("verify", commands[4])
        self.assertIn("--require-qualified", commands[4])
        for name, value in {
            "--site-dir": publication.SITE_DIR,
            "--site-url": publication.SITE_URL,
            "--standard-sha": "a" * 40,
            "--source-identity": publication.SOURCE_RECEIPT,
            "--build-identity": "artifacts/website-security/build-identity.json",
            "--verification-report": "artifacts/website-security/site-verification.json",
            "--csp-report": "artifacts/website-security/csp.json",
            "--output": publication.MANIFEST,
        }.items():
            self.assertEqual(commands[3][commands[3].index(name) + 1], value)
        self.assertEqual(
            commands[4][commands[4].index("--manifest") + 1], publication.MANIFEST
        )
        self.assertFalse((self.root / publication.MANIFEST).exists())

    def test_failed_renderer_stops_before_manifest_admission(self) -> None:
        self.source()
        calls: list[tuple[str, ...]] = []

        def child(root: Path, *arguments: str, authority: str | None = None) -> None:
            calls.append(arguments)
            if arguments[1].endswith("render_publication.py"):
                raise subprocess.CalledProcessError(1, arguments)

        with (
            patch.object(
                publication,
                "accepted_standard",
                return_value=publication.STANDARD_ROOT + "/" + "a" * 40,
            ),
            patch.object(publication, "command", child),
            self.assertRaises(subprocess.CalledProcessError),
        ):
            publication.build(self.root)
        self.assertEqual(len(calls), 3)
        self.assertFalse(any("admit" in args for args in calls))
        self.assertFalse((self.root / publication.MANIFEST).exists())
        self.observations.append(
            {
                "kind": "controlled-renderer-rejection",
                "calls": calls,
                "publication_approval": False,
            }
        )

    def test_verify_only_rechecks_qualified_manifest_without_building_or_rewriting(
        self,
    ) -> None:
        calls: list[tuple[str, ...]] = []
        with patch.object(
            publication, "command", lambda root, *args, **kwargs: calls.append(args)
        ):
            publication.verify(self.root)
        self.assertEqual(len(calls), 1)
        self.assertIn("verify", calls[0])
        self.assertIn("--require-qualified", calls[0])
        self.assertFalse(
            any("capture-source" in args or "admit" in args for args in calls)
        )
        self.observations.append(
            {
                "kind": "controlled-readonly-verify-interface",
                "calls": calls,
                "publication_approval": False,
            }
        )

    def test_real_verify_rejects_absent_manifest(self) -> None:
        script = self.root / ".bijux/shared/bijux-docs/security/publication.py"
        script.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / ".bijux/shared/bijux-docs/security/publication.py", script)
        result = self.make("gh-docs-verify")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("publication rejected", result.stderr)
        self.assertFalse((self.root / publication.MANIFEST).exists())

    def controlled_standard(self) -> tuple[Path, str, str]:
        """Create local Git transport data, never a publication-approved authority."""
        source = self.root / "artifacts/controlled-standard"
        source.mkdir(parents=True)

        def git(*arguments: str) -> str:
            return subprocess.check_output(
                ["git", "-C", str(source), *arguments], text=True
            ).strip()

        git("init", "-q")
        git("config", "user.email", "bijux@example.invalid")
        git("config", "user.name", "Bijux cache controls")
        (source / "source.txt").write_text("Initial controlled bytes\n")
        git("add", "source.txt")
        git("commit", "-qm", "test(docs): define local cache transport")
        first = git("rev-parse", "HEAD")
        (source / "source.txt").write_text("Successor controlled bytes\n")
        git("add", "source.txt")
        git("commit", "-qm", "test(docs): vary controlled source identity")
        return source, first, git("rev-parse", "HEAD")

    def transport(
        self, source: Path, interrupt: bool = False
    ) -> AbstractContextManager[object]:
        actual = publication.command
        failed = False

        def execute(root: Path, *arguments: str, authority: str | None = None) -> None:
            nonlocal failed
            requested = arguments
            if "fetch" in arguments:
                if interrupt and not failed:
                    failed = True
                    self.observations.append(
                        {
                            "kind": "controlled-fetch-interruption",
                            "requested_command": list(arguments),
                            "external_fetch_executed": False,
                        }
                    )
                    raise subprocess.CalledProcessError(1, arguments)
                arguments = tuple(
                    str(source) if item == "origin" else item for item in arguments
                )
            self.observations.append(
                {
                    "kind": "actual-local-Git-cache-command",
                    "requested_command": list(requested),
                    "executed_command": list(arguments),
                    "authority": authority,
                    "external_fetch_executed": False,
                    "publication_approval": False,
                }
            )
            return actual(root, *arguments, authority=authority)

        return patch.object(publication, "command", execute)

    def test_existing_standard_cache_is_preserved_for_independent_identity_validation(
        self,
    ) -> None:
        source, pin, _ = self.controlled_standard()
        with self.transport(source):
            relative = publication.accepted_standard(self.root, pin)
        marker = self.root / relative / ".git" / "preserved-marker"
        marker.write_text("Preserve this owned metadata\n")
        with patch.object(publication, "command") as child:
            self.assertEqual(publication.accepted_standard(self.root, pin), relative)
        child.assert_not_called()
        self.assertEqual(marker.read_text(), "Preserve this owned metadata\n")
        self.observations.append(
            {"kind": "local-Git-cache-only", "pin": pin, "publication_approval": False}
        )

    def test_distinct_pins_coexist_without_resetting_the_previous_checkout(
        self,
    ) -> None:
        source, first, second = self.controlled_standard()
        with self.transport(source):
            previous = publication.accepted_standard(self.root, first)
            current = publication.accepted_standard(self.root, second)
        self.assertNotEqual(previous, current)
        self.assertEqual(
            (self.root / previous / "source.txt").read_text(),
            "Initial controlled bytes\n",
        )
        self.assertEqual(
            (self.root / current / "source.txt").read_text(),
            "Successor controlled bytes\n",
        )
        self.observations.append(
            {
                "kind": "controlled-coexisting-Git-pins",
                "pins": [first, second],
                "publication_approval": False,
            }
        )

    def test_interrupted_owned_fetch_resumes_without_deleting_prior_cache(self) -> None:
        source, pin, _ = self.controlled_standard()
        with self.transport(source, interrupt=True):
            with self.assertRaises(subprocess.CalledProcessError):
                publication.accepted_standard(self.root, pin)
            relative = publication.accepted_standard(self.root, pin)
        self.assertEqual(
            (self.root / relative / "source.txt").read_text(),
            "Initial controlled bytes\n",
        )
        self.observations.append(
            {
                "kind": "actual-owned-Git-init-and-controlled-fetch-recovery",
                "pin": pin,
                "publication_approval": False,
            }
        )

    def test_interrupted_owned_initialization_resumes_inside_consumer_git(self) -> None:
        self.source()
        source, pin, _ = self.controlled_standard()
        actual = publication.command

        def interrupted(
            root: Path, *arguments: str, authority: str | None = None
        ) -> None:
            if "init" in arguments:
                Path(arguments[-1]).mkdir(parents=True)
                raise subprocess.CalledProcessError(1, arguments)
            return actual(root, *arguments, authority=authority)

        with (
            patch.object(publication, "command", interrupted),
            self.assertRaises(subprocess.CalledProcessError),
        ):
            publication.accepted_standard(self.root, pin)
        with self.transport(source):
            relative = publication.accepted_standard(self.root, pin)
        self.assertEqual(
            (self.root / relative / "source.txt").read_text(),
            "Initial controlled bytes\n",
        )
        self.observations.append(
            {
                "kind": "controlled-owned-initialization-recovery",
                "pin": pin,
                "publication_approval": False,
            }
        )

    def test_dirty_existing_cache_rejects_before_fetch_or_checkout(self) -> None:
        source, pin, _ = self.controlled_standard()
        with self.transport(source):
            relative = publication.accepted_standard(self.root, pin)
        content = self.root / relative / "source.txt"
        content.write_text("Preserve unreviewed user bytes\n")
        with (
            patch.object(publication, "command") as child,
            self.assertRaisesRegex(ValueError, "dirty standard cache"),
        ):
            publication.accepted_standard(self.root, pin)
        child.assert_not_called()
        self.assertEqual(content.read_text(), "Preserve unreviewed user bytes\n")

    def test_unowned_incomplete_cache_is_preserved_and_rejected(self) -> None:
        cache = self.root / publication.STANDARD_ROOT / ("a" * 40)
        cache.mkdir(parents=True)
        marker = cache / "user-owned-input"
        marker.write_text("Preserve\n")
        with (
            patch.object(publication, "command") as child,
            self.assertRaisesRegex(ValueError, "unowned or incomplete"),
        ):
            publication.accepted_standard(self.root, "a" * 40)
        child.assert_not_called()
        self.assertEqual(marker.read_text(), "Preserve\n")

    def test_legacy_fixed_cache_is_preserved_beside_new_pin_checkouts(self) -> None:
        source, pin, _ = self.controlled_standard()
        legacy = self.root / "artifacts/website-security/accepted-standard"
        legacy.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", "--quiet", str(source), str(legacy)], check=True
        )
        before = {
            path.relative_to(legacy).as_posix(): path.read_bytes()
            for path in legacy.rglob("*")
            if path.is_file()
        }
        with self.transport(source):
            relative = publication.accepted_standard(self.root, pin)
        self.assertTrue((self.root / relative / "source.txt").is_file())
        after = {
            path.relative_to(legacy).as_posix(): path.read_bytes()
            for path in legacy.rglob("*")
            if path.is_file()
        }
        self.assertEqual(before, after)
        self.assertEqual(
            subprocess.check_output(
                ["git", "-C", str(legacy), "status", "--porcelain"], text=True
            ),
            "",
        )
        self.observations.append(
            {
                "kind": "complete-legacy-Git-cache-byte-preservation",
                "files": len(before),
                "publication_approval": False,
            }
        )

    def test_command_environment_uses_the_same_pin_cache_as_checkpoint(self) -> None:
        relative = publication.STANDARD_ROOT + "/" + "a" * 40
        with patch.object(subprocess, "run") as child:
            publication.command(
                self.root, sys.executable, "--version", authority=relative
            )
        environment = child.call_args.kwargs["env"]
        self.assertEqual(environment["BIJUX_STD_ROOT"], str(self.root / relative))
        self.assertEqual(environment["DOCS_PYTHON"], sys.executable)
        self.observations.append(
            {
                "kind": "controlled-selected-command-environment",
                "standard_root": environment["BIJUX_STD_ROOT"],
                "publication_approval": False,
            }
        )

    def test_cache_git_metadata_symlink_rejects_before_mutation(self) -> None:
        cache = self.root / publication.STANDARD_ROOT / ("a" * 40)
        cache.mkdir(parents=True)
        outside = self.root / "artifacts/user-owned-git"
        outside.mkdir()
        (cache / ".git").symlink_to(outside, target_is_directory=True)
        with (
            patch.object(publication, "command") as child,
            self.assertRaisesRegex(ValueError, "symlinks"),
        ):
            publication.accepted_standard(self.root, "a" * 40)
        child.assert_not_called()
        self.assertTrue((cache / ".git").is_symlink())

    def test_existing_wrong_origin_is_preserved_and_rejected(self) -> None:
        source, pin, _ = self.controlled_standard()
        with self.transport(source):
            relative = publication.accepted_standard(self.root, pin)
        cache = self.root / relative
        subprocess.run(
            [
                "git",
                "-C",
                str(cache),
                "remote",
                "set-url",
                "origin",
                "https://example.invalid/unreviewed.git",
            ],
            check=True,
        )
        before = (cache / ".git/config").read_bytes()
        with (
            patch.object(publication, "command") as child,
            self.assertRaisesRegex(ValueError, "origin differs"),
        ):
            publication.accepted_standard(self.root, pin)
        child.assert_not_called()
        self.assertEqual((cache / ".git/config").read_bytes(), before)

    def test_symlink_standard_cache_rejects_before_fetch(self) -> None:
        outside = self.root / "artifacts/other-source"
        outside.mkdir(parents=True)
        cache = self.root / publication.STANDARD_ROOT
        cache.parent.mkdir(parents=True)
        cache.symlink_to(outside, target_is_directory=True)
        with (
            patch.object(publication, "command") as child,
            self.assertRaisesRegex(ValueError, "symlinks"),
        ):
            publication.accepted_standard(self.root, "a" * 40)
        child.assert_not_called()


if __name__ == "__main__":
    unittest.main()
