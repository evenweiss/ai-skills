"""Exercise the version CLI against temporary local Git repositories."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("version.py")
ENV = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")


class VersionTests(unittest.TestCase):
    def calculate(self, mode, bump=None, branch=None, base="2.4.7"):
        with tempfile.TemporaryDirectory(prefix="git-flow-version-") as temp:
            root = Path(temp)
            repo, remote = root / "repo", root / "remote.git"

            def git(*args):
                return subprocess.check_output(
                    ["git", "-C", str(repo), *args], env=ENV, text=True,
                    stderr=subprocess.PIPE,
                ).strip()

            subprocess.run(
                ["git", "init", "--quiet", "--bare", str(remote)],
                env=ENV, check=True, capture_output=True,
            )
            subprocess.run(
                ["git", "init", "--quiet", "--initial-branch=master", str(repo)],
                env=ENV, check=True, capture_output=True,
            )
            git("config", "user.name", "Version Test")
            git("config", "user.email", "version-test@example.invalid")
            git("commit", "--quiet", "--allow-empty", "-m", "baseline")
            git("tag", base)
            git("remote", "add", "origin", str(remote))
            git("push", "--quiet", "--no-follow-tags", "origin", "master", base)
            before = git("for-each-ref", "--format=%(refname) %(objectname)")
            command = [
                sys.executable, str(SCRIPT), mode, "--repo", str(repo),
                "--remote", "origin", "--production", "master",
            ]
            if bump:
                command += ["--bump", bump]
            if branch:
                command += ["--branch", branch]
            result = subprocess.run(command, env=ENV, capture_output=True, text=True)
            self.assertEqual(before, git("for-each-ref", "--format=%(refname) %(objectname)"))
            self.assertEqual("", git("status", "--porcelain"))
            return result

    def assert_candidate(self, expected, **kwargs):
        result = self.calculate(**kwargs)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(expected, json.loads(result.stdout)["candidate"])

    def test_finish_uses_assessed_level_instead_of_branch_type(self):
        for mode, branch, bump, expected in [
            ("finish-feature", "feature/docs", "patch", "2.4.8"),
            ("finish-feature", "feature/parser", "major", "3.0.0"),
            ("finish-hotfix", "hotfix/2.4.8", "minor", "2.5.0"),
            ("finish-hotfix", "hotfix/2.4.8", "major", "3.0.0"),
        ]:
            with self.subTest(mode=mode, bump=bump):
                self.assert_candidate(expected, mode=mode, branch=branch, bump=bump)

    def test_zero_versions_use_the_level_selected_by_project_policy(self):
        for base, bump, expected in [
            ("0.0.3", "patch", "0.0.4"),
            ("0.0.3", "minor", "0.1.0"),
            ("0.3.8", "minor", "0.4.0"),
            ("0.3.8", "major", "1.0.0"),
        ]:
            with self.subTest(base=base, bump=bump):
                self.assert_candidate(expected, mode="finish-feature", bump=bump, base=base)

    def test_all_finish_modes_require_an_assessed_level(self):
        for mode in ["finish-feature", "finish-hotfix", "finish-release"]:
            with self.subTest(mode=mode):
                result = self.calculate(mode, branch="release/2.5.0")
                self.assertEqual(2, result.returncode)
                self.assertEqual("error", json.loads(result.stderr)["status"])

    def test_release_rejects_target_below_required_level(self):
        result = self.calculate("finish-release", bump="major", branch="release/2.5.0")
        self.assertEqual(2, result.returncode)
        self.assertTrue(result.stderr.lstrip().startswith("{"), result.stderr)
        self.assertEqual("error", json.loads(result.stderr)["status"])

    def test_release_preserves_a_sufficient_explicit_target(self):
        self.assert_candidate(
            "3.2.0", mode="finish-release", bump="major", branch="release/3.2.0",
        )

    def test_branch_creation_keeps_its_existing_contract(self):
        self.assert_candidate("hotfix/2.4.8", mode="create-hotfix")
        self.assert_candidate("2.5.0", mode="create-release", branch="release/2.5.0")


if __name__ == "__main__":
    unittest.main()
