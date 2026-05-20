from __future__ import annotations

import json
import subprocess
import sys
import unittest
import shutil
from contextlib import contextmanager
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "dag_status.py"
TMP_ROOT = ROOT / "tmp_tests"


def write(path: Path, text: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class DagStatusTests(unittest.TestCase):
    @contextmanager
    def temp_project(self, name: str):
        TMP_ROOT.mkdir(exist_ok=True)
        path = TMP_ROOT / name
        shutil.rmtree(path, ignore_errors=True)
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def run_status(self, root: Path, *args: str) -> dict:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(root), *args],
            cwd=str(ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        return json.loads(result.stdout)

    def node(self, payload: dict, node_id: str) -> dict:
        return next(node for node in payload["nodes"] if node["id"] == node_id)

    def test_empty_project_starts_with_project_profile(self) -> None:
        with self.temp_project("empty") as root:
            payload = self.run_status(root)

        self.assertEqual(payload["next"], ["project-profile"])
        self.assertEqual(self.node(payload, "project-profile")["status"], "ready")
        self.assertEqual(self.node(payload, "openspec-artifacts")["status"], "blocked")

    def test_brainstorm_summary_makes_openspec_ready(self) -> None:
        with self.temp_project("brainstorm") as root:
            write(root / ".hyperspec-brainstorm.md", "## Goals\nShip it\n")
            payload = self.run_status(root)

        self.assertEqual(self.node(payload, "brainstorm")["status"], "done")
        self.assertIn("openspec-artifacts", payload["next"])

    def test_openspec_artifacts_make_plan_ready(self) -> None:
        with self.temp_project("artifacts") as root:
            change = root / "openspec" / "changes" / "add-login"
            write(change / "proposal.md")
            write(change / "design.md")
            write(change / "tasks.md")
            write(change / "specs" / "auth" / "spec.md")
            payload = self.run_status(root)

        self.assertEqual(payload["activeChange"], "add-login")
        self.assertEqual(self.node(payload, "openspec-artifacts")["status"], "done")
        self.assertIn("implementation-plan", payload["next"])

    def test_explicit_change_selects_plan_when_multiple_changes_exist(self) -> None:
        with self.temp_project("explicit-change") as root:
            for name in ("add-login", "add-billing"):
                change = root / "openspec" / "changes" / name
                write(change / "proposal.md")
                write(change / "design.md")
                write(change / "tasks.md")
                write(change / "specs" / "domain" / "spec.md")
            write(
                root / "superpowers" / "plans" / "2026-05-20-add-billing.md",
                "<!-- hyperspec change: add-billing -->\n- [ ] implement billing\n",
            )
            payload = self.run_status(root, "--change", "add-billing")

        self.assertEqual(payload["activeChange"], "add-billing")
        self.assertTrue(payload["explicitChange"])
        self.assertEqual(self.node(payload, "implementation-plan")["status"], "done")
        self.assertIn("implementation", payload["next"])

    def test_archive_with_no_state_is_complete(self) -> None:
        with self.temp_project("archive-complete") as root:
            archive = root / "openspec" / "changes" / "archive" / "2026-05-20-add-login"
            write(archive / "proposal.md")
            write(archive / "brainstorm.md")
            payload = self.run_status(root, "--change", "add-login")

        self.assertEqual(self.node(payload, "archive")["status"], "done")
        self.assertEqual(self.node(payload, "cleanup")["status"], "done")
        self.assertTrue(payload["isComplete"])

    def test_change_scoped_state_overrides_top_level_checkpoint(self) -> None:
        with self.temp_project("change-scoped-state") as root:
            write(
                root / ".hyperspec-state.yaml",
                "\n".join(
                    [
                        "version: 1",
                        "active_change: add-login",
                        "phase: apply",
                        "checkpoint: verified",
                        "changes:",
                        "  add-login:",
                        "    phase: apply",
                        "    checkpoint: reviewed",
                        "  add-billing:",
                        "    phase: apply",
                        "    checkpoint: plan-generated-and-confirmed",
                        "project_profile:",
                        "  languages: [python]",
                    ]
                ),
            )
            payload = self.run_status(root, "--change", "add-billing")

        self.assertEqual(payload["activeChange"], "add-billing")
        self.assertTrue(payload["changeScoped"])
        self.assertEqual(payload["checkpoint"], "plan-generated-and-confirmed")
        self.assertEqual(self.node(payload, "verification")["status"], "blocked")
        self.assertEqual(self.node(payload, "review")["status"], "blocked")


if __name__ == "__main__":
    unittest.main()
