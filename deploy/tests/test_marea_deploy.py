"""Tests for the pull-based deploy agent.

The agent decides whether a commit may ship, so the tests are mostly about the
gates: the exact SHA, the push event, a fast-forward checkout and a clean tree.
The deploy and rollback flow is driven with a fake command runner and a fake
health endpoint; nothing here touches Git, npm, systemd or the network.
"""

from __future__ import annotations

import logging
import sys
import unittest
from pathlib import Path
from subprocess import CompletedProcess

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import marea_deploy as agent

agent.LOG.addHandler(logging.NullHandler())
agent.LOG.propagate = False

OLD = "a" * 40
NEW = "b" * 40
THIRD = "c" * 40


def run_payload(
    *,
    sha: str = NEW,
    branch: str = "main",
    event: str = "push",
    status: str = "completed",
    conclusion: str | None = "success",
    created_at: str = "2026-01-01T00:00:00Z",
) -> dict:
    return {
        "workflow_runs": [
            {
                "head_sha": sha,
                "head_branch": branch,
                "event": event,
                "status": status,
                "conclusion": conclusion,
                "created_at": created_at,
            }
        ]
    }


class FakeRunner:
    def __init__(self, handler):
        self.calls: list[tuple[str, ...]] = []
        self.handler = handler

    def __call__(self, argv, *, cwd, check=True):
        command = tuple(str(part) for part in argv)
        self.calls.append(command)
        code, stdout, stderr = self.handler(command)
        return CompletedProcess(command, code, stdout, stderr)


def handler(
    *,
    head: str = OLD,
    remote: str = NEW,
    fetched: str | None = None,
    status: str = "",
    branch: str | None = "main",
    ancestor: int = 0,
    failures: set[tuple[str, ...]] | None = None,
):
    failures = failures or set()
    fetched = remote if fetched is None else fetched

    def handle(command):
        if command in failures:
            return 1, "", "simulated failure"
        if command == ("git", "status", "--porcelain"):
            return 0, status, ""
        if command == ("git", "symbolic-ref", "--quiet", "--short", "HEAD"):
            return (0, f"{branch}\n", "") if branch else (1, "", "")
        if command == ("git", "rev-parse", "HEAD"):
            return 0, f"{head}\n", ""
        if command[:2] == ("git", "ls-remote"):
            return 0, f"{remote}\trefs/heads/main\n", ""
        if command[:2] == ("git", "fetch"):
            return 0, "", ""
        if command == ("git", "rev-parse", "origin/main"):
            return 0, f"{fetched}\n", ""
        if command[:3] == ("git", "merge-base", "--is-ancestor"):
            return ancestor, "", ""
        if command[:2] in (("git", "merge"), ("git", "reset")):
            return 0, "", ""
        if command[0].endswith("/pip") or command[:2] == ("python3", "-m"):
            return 0, "", ""
        if command[:2] in (("npm", "ci"), ("npm", "run")):
            return 0, "", ""
        if command[:3] == ("sudo", "-n", "systemctl"):
            return 0, "", ""
        return 0, "", ""

    return handle


class Harness:
    def __init__(
        self,
        tmp_path: Path,
        *,
        payload=None,
        health=True,
        runner_handler=None,
        config=None,
    ):
        self.config = config or agent.Config(
            repo="owner/repo",
            checkout=tmp_path,
            service="marea-alta",
            health_timeout=0.3,
            health_interval=0.1,
        )
        self.runner = FakeRunner(runner_handler or handler())
        self.json_calls: list[tuple[str, str | None]] = []
        self.health_calls: list[str] = []
        self.payload = payload if payload is not None else run_payload()
        self.health = health

        def http_json(url, token=None):
            self.json_calls.append((url, token))
            if callable(self.payload):
                return self.payload(url, token)
            return self.payload

        def check_health(url):
            self.health_calls.append(url)
            if callable(self.health):
                return self.health(url)
            return self.health

        self.deployer = agent.Deployer(
            self.config,
            run=self.runner,
            http_json=http_json,
            health=check_health,
            sleep=lambda _seconds: None,
        )

    def commands(self) -> list[tuple[str, ...]]:
        return self.runner.calls


class DeployFlowTests(unittest.TestCase):
    def test_deploys_a_green_commit(self):
        with self.subTest("happy path"):
            import tempfile

            with tempfile.TemporaryDirectory() as directory:
                harness = Harness(Path(directory))

                self.assertEqual(harness.deployer.deploy(), 0)

                commands = harness.commands()
                self.assertIn(("git", "merge", "--ff-only", NEW), commands)
                self.assertIn(("npm", "ci", "--no-audit", "--no-fund"), commands)
                self.assertIn(("npm", "run", "build"), commands)
                self.assertIn(
                    ("sudo", "-n", "systemctl", "restart", "marea-alta"), commands
                )
                self.assertEqual(len(harness.json_calls), 1)
                url, token = harness.json_calls[0]
                self.assertIn("/actions/workflows/ci.yml/runs", url)
                self.assertIn("branch=main", url)
                self.assertIn("event=push", url)
                self.assertIsNone(token)
                self.assertEqual(harness.health_calls, ["http://127.0.0.1:8000/healthz"])
                state = Path(directory) / ".git" / "marea-deploy.state"
                self.assertEqual(state.read_text(encoding="utf-8").strip(), NEW)

    def test_does_nothing_when_the_checkout_already_matches_main(self):
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            checkout = Path(directory)
            state = checkout / ".git" / "marea-deploy.state"
            state.parent.mkdir()
            state.write_text(NEW + "\n", encoding="utf-8")
            harness = Harness(
                checkout,
                runner_handler=handler(head=NEW, remote=NEW),
            )
            harness.payload = lambda _url, _token: self.fail("API must not be called")

            self.assertEqual(harness.deployer.deploy(), 0)
            self.assertNotIn(
                ("git", "fetch", "--prune", "origin", "main"), harness.commands()
            )

    def test_reconciles_when_the_state_file_is_missing(self):
        """A crash after `git merge` leaves main checked out but not deployed."""
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            checkout = Path(directory)
            harness = Harness(
                checkout,
                runner_handler=handler(head=NEW, remote=NEW),
            )

            self.assertEqual(harness.deployer.deploy(), 0)

            commands = harness.commands()
            self.assertNotIn(("git", "merge", "--ff-only", NEW), commands)
            self.assertIn(("npm", "run", "build"), commands)
            self.assertIn(
                ("sudo", "-n", "systemctl", "restart", "marea-alta"), commands
            )
            state = checkout / ".git" / "marea-deploy.state"
            self.assertEqual(state.read_text(encoding="utf-8").strip(), NEW)

    def test_reconcile_still_waits_for_ci(self):
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(
                Path(directory),
                payload=run_payload(status="in_progress", conclusion=None),
                runner_handler=handler(head=NEW, remote=NEW),
            )

            self.assertEqual(harness.deployer.deploy(), 0)
            self.assertNotIn(("npm", "run", "build"), harness.commands())

    def test_waits_for_a_pending_ci_run(self):
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(
                Path(directory),
                payload=run_payload(status="in_progress", conclusion=None),
            )

            self.assertEqual(harness.deployer.deploy(), 0)
            self.assertNotIn(
                ("git", "fetch", "--prune", "origin", "main"), harness.commands()
            )
            self.assertEqual(harness.health_calls, [])

    def test_never_deploys_a_failed_ci_run(self):
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(
                Path(directory),
                payload=run_payload(conclusion="failure"),
            )

            self.assertEqual(harness.deployer.deploy(), 0)
            self.assertNotIn(
                ("git", "fetch", "--prune", "origin", "main"), harness.commands()
            )

    def test_refuses_a_commit_that_is_not_a_fast_forward(self):
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(
                Path(directory),
                runner_handler=handler(ancestor=1),
            )

            with self.assertRaisesRegex(agent.DeployError, "not a fast-forward"):
                harness.deployer.deploy()

            self.assertNotIn(("git", "merge", "--ff-only", NEW), harness.commands())
            self.assertEqual(harness.health_calls, [])

    def test_refuses_a_dirty_checkout(self):
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(
                Path(directory),
                runner_handler=handler(status=" M backend/app/main.py\n"),
            )

            with self.assertRaisesRegex(agent.DeployError, "local changes"):
                harness.deployer.deploy()

            self.assertEqual(harness.json_calls, [])

    def test_refuses_a_detached_head(self):
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(
                Path(directory),
                runner_handler=handler(branch=None),
            )

            with self.assertRaisesRegex(agent.DeployError, "detached HEAD"):
                harness.deployer.deploy()

            self.assertEqual(harness.json_calls, [])

    def test_retries_when_main_moves_during_the_check(self):
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(
                Path(directory),
                runner_handler=handler(remote=NEW, fetched=THIRD),
            )

            self.assertEqual(harness.deployer.deploy(), 0)
            self.assertNotIn(("git", "merge", "--ff-only", NEW), harness.commands())

    def test_rolls_back_when_the_new_version_never_gets_healthy(self):
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            outcomes = iter([False, False, False, True])
            harness = Harness(Path(directory), health=lambda _url: next(outcomes))

            with self.assertRaisesRegex(agent.DeployError, "did not return 200"):
                harness.deployer.deploy()

            commands = harness.commands()
            self.assertIn(("git", "reset", "--hard", OLD), commands)
            restarts = [
                command
                for command in commands
                if command[:3] == ("sudo", "-n", "systemctl")
            ]
            self.assertEqual(len(restarts), 2)
            state = Path(directory) / ".git" / "marea-deploy.state"
            self.assertEqual(state.read_text(encoding="utf-8").strip(), OLD)

    def test_reports_when_the_rollback_also_fails(self):
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(Path(directory), health=False)

            with self.assertRaisesRegex(agent.DeployError, "also failed"):
                harness.deployer.deploy()

            self.assertIn(("git", "reset", "--hard", OLD), harness.commands())


class CiStateTests(unittest.TestCase):
    def test_accepts_only_a_successful_push_on_the_same_branch_and_commit(self):
        self.assertEqual(agent.ci_state(run_payload(), NEW, "main"), "success")
        self.assertEqual(
            agent.ci_state(run_payload(sha=OLD), NEW, "main"), "missing"
        )
        self.assertEqual(
            agent.ci_state(run_payload(branch="feature"), NEW, "main"), "missing"
        )
        self.assertEqual(
            agent.ci_state(run_payload(event="pull_request"), NEW, "main"), "missing"
        )

    def test_reports_pending_and_failed_runs(self):
        self.assertEqual(
            agent.ci_state(
                run_payload(status="queued", conclusion=None), NEW, "main"
            ),
            "pending",
        )
        self.assertEqual(
            agent.ci_state(run_payload(conclusion="failure"), NEW, "main"),
            "not successful (failure)",
        )
        self.assertEqual(agent.ci_state({"workflow_runs": []}, NEW, "main"), "missing")
        self.assertEqual(agent.ci_state({}, NEW, "main"), "missing")

    def test_uses_the_newest_matching_run(self):
        payload = {
            "workflow_runs": [
                {
                    "head_sha": NEW,
                    "head_branch": "main",
                    "event": "push",
                    "status": "completed",
                    "conclusion": "failure",
                    "created_at": "2026-01-01T00:00:00Z",
                },
                {
                    "head_sha": NEW,
                    "head_branch": "main",
                    "event": "push",
                    "status": "completed",
                    "conclusion": "success",
                    "created_at": "2026-01-02T00:00:00Z",
                },
            ]
        }

        self.assertEqual(agent.ci_state(payload, NEW, "main"), "success")


class ConfigTests(unittest.TestCase):
    def test_reads_the_required_values_and_defaults(self):
        config = agent.Config.from_env(
            {
                "DEPLOY_REPO": "owner/repo",
                "DEPLOY_CHECKOUT": "/srv/marea",
                "DEPLOY_SERVICE": "marea-alta",
            }
        )

        self.assertEqual(config.repo, "owner/repo")
        self.assertEqual(config.checkout, Path("/srv/marea"))
        self.assertEqual(config.branch, "main")
        self.assertEqual(config.workflow, "ci.yml")
        self.assertEqual(config.git_remote, "origin")
        self.assertEqual(config.health_url, "http://127.0.0.1:8000/healthz")
        self.assertEqual(
            config.lock_file, Path("/srv/marea/.git/marea-deploy.lock")
        )
        self.assertEqual(
            config.state_file, Path("/srv/marea/.git/marea-deploy.state")
        )
        self.assertIsNone(config.token_file)

    def test_reads_optional_values(self):
        config = agent.Config.from_env(
            {
                "DEPLOY_REPO": "owner/repo",
                "DEPLOY_CHECKOUT": "/srv/marea",
                "DEPLOY_SERVICE": "marea-alta",
                "DEPLOY_BRANCH": "production",
                "DEPLOY_WORKFLOW": "checks.yml",
                "DEPLOY_GITHUB_TOKEN_FILE": "/etc/marea-deploy/token",
                "DEPLOY_LOCK_FILE": "/run/marea.lock",
                "DEPLOY_STATE_FILE": "/var/lib/marea-deploy/state",
                "DEPLOY_HEALTH_TIMEOUT": "30",
                "DEPLOY_HEALTH_INTERVAL": "1",
            }
        )

        self.assertEqual(config.branch, "production")
        self.assertEqual(config.workflow, "checks.yml")
        self.assertEqual(config.token_file, Path("/etc/marea-deploy/token"))
        self.assertEqual(config.lock_file, Path("/run/marea.lock"))
        self.assertEqual(config.state_file, Path("/var/lib/marea-deploy/state"))
        self.assertEqual(config.health_timeout, 30.0)
        self.assertEqual(config.health_interval, 1.0)

    def test_rejects_a_missing_identity_or_a_bad_repository_name(self):
        base = {
            "DEPLOY_REPO": "owner/repo",
            "DEPLOY_CHECKOUT": "/srv/marea",
            "DEPLOY_SERVICE": "marea-alta",
        }
        for missing in ("DEPLOY_REPO", "DEPLOY_CHECKOUT", "DEPLOY_SERVICE"):
            values = dict(base)
            values.pop(missing)
            with self.assertRaisesRegex(agent.DeployError, missing):
                agent.Config.from_env(values)

        with self.assertRaisesRegex(agent.DeployError, "owner/name"):
            agent.Config.from_env({**base, "DEPLOY_REPO": "owner"})

    def test_rejects_bad_health_timing(self):
        base = {
            "DEPLOY_REPO": "owner/repo",
            "DEPLOY_CHECKOUT": "/srv/marea",
            "DEPLOY_SERVICE": "marea-alta",
            "DEPLOY_HEALTH_TIMEOUT": "soon",
        }
        with self.assertRaisesRegex(agent.DeployError, "must be numbers"):
            agent.Config.from_env(base)

        with self.assertRaisesRegex(agent.DeployError, "must be positive"):
            agent.Config.from_env({**base, "DEPLOY_HEALTH_TIMEOUT": "0"})


if __name__ == "__main__":
    unittest.main()
