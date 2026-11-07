#!/usr/bin/env python3
"""Deploy Marea Alta from the VPS, after GitHub Actions says the commit is green.

The VPS pulls; GitHub never pushes. There is no inbound SSH from Actions, no
private key in the repository or in GitHub secrets, and no long-lived credential
on the runner. A systemd timer runs this script every few minutes:

1. `git ls-remote` the branch. If it matches the checkout, stop — no API call.
2. Ask the GitHub API for the latest push run of the CI workflow. Deploy only
   when that run completed successfully for the exact commit.
3. Fast-forward the checkout, install backend dependencies, build the frontend,
   restart the service and wait for `/healthz`.
4. On any failure, reset to the previous commit, rebuild and restart, then exit
   non-zero so systemd records the failure.

Configuration comes from `/etc/marea-deploy.env`; see
`marea-deploy.env.example`. Only the Python standard library is used, so the
agent can run before the app's virtualenv has been updated.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import logging
import math
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

LOG = logging.getLogger("marea-deploy")
GITHUB_API = "https://api.github.com"
USER_AGENT = "marea-deploy"


class DeployError(RuntimeError):
    """A condition that needs a human, not another poll."""


@dataclass(frozen=True)
class Config:
    """Everything the agent needs, read once from the environment file."""

    repo: str
    checkout: Path
    service: str
    branch: str = "main"
    health_url: str = "http://127.0.0.1:8000/healthz"
    workflow: str = "ci.yml"
    git_remote: str = "origin"
    token_file: Path | None = None
    lock_file: Path = Path("/run/lock/marea-deploy.lock")
    state_file: Path | None = None
    health_timeout: float = 60.0
    health_interval: float = 2.0

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Config:
        values = os.environ if env is None else env

        def required(name: str) -> str:
            value = values.get(name, "").strip()
            if not value:
                raise DeployError(f"{name} is not set")
            return value

        repo = required("DEPLOY_REPO")
        if repo.count("/") != 1 or not all(repo.split("/")):
            raise DeployError("DEPLOY_REPO must look like owner/name")

        checkout = Path(required("DEPLOY_CHECKOUT")).expanduser()
        service = required("DEPLOY_SERVICE")

        try:
            health_timeout = float(values.get("DEPLOY_HEALTH_TIMEOUT", "60"))
            health_interval = float(values.get("DEPLOY_HEALTH_INTERVAL", "2"))
        except ValueError as exc:
            raise DeployError("DEPLOY_HEALTH_TIMEOUT and DEPLOY_HEALTH_INTERVAL must be numbers") from exc
        if health_timeout <= 0 or health_interval <= 0:
            raise DeployError("DEPLOY_HEALTH_TIMEOUT and DEPLOY_HEALTH_INTERVAL must be positive")

        token_raw = values.get("DEPLOY_GITHUB_TOKEN_FILE", "").strip()
        lock_raw = values.get("DEPLOY_LOCK_FILE", "").strip()
        state_raw = values.get("DEPLOY_STATE_FILE", "").strip()

        return cls(
            repo=repo,
            checkout=checkout,
            service=service,
            branch=values.get("DEPLOY_BRANCH", "main").strip() or "main",
            health_url=values.get(
                "DEPLOY_HEALTH_URL", "http://127.0.0.1:8000/healthz"
            ).strip(),
            workflow=values.get("DEPLOY_WORKFLOW", "ci.yml").strip() or "ci.yml",
            git_remote=values.get("DEPLOY_GIT_REMOTE", "origin").strip() or "origin",
            token_file=Path(token_raw).expanduser() if token_raw else None,
            lock_file=(
                Path(lock_raw).expanduser()
                if lock_raw
                else checkout / ".git" / "marea-deploy.lock"
            ),
            state_file=(
                Path(state_raw).expanduser()
                if state_raw
                else checkout / ".git" / "marea-deploy.state"
            ),
            health_timeout=health_timeout,
            health_interval=health_interval,
        )


def run_command(
    argv: Sequence[object], *, cwd: Path, check: bool = True
) -> subprocess.CompletedProcess[str]:
    """Run one command, logging it without ever logging a token."""
    command = [str(part) for part in argv]
    LOG.info("+ %s", " ".join(command))
    result = subprocess.run(
        command, check=False, cwd=str(cwd), text=True, capture_output=True
    )
    if result.stdout.strip():
        LOG.debug("%s", result.stdout.strip())
    if result.stderr.strip():
        LOG.debug("%s", result.stderr.strip())
    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        message = detail[-1] if detail else "no output"
        raise DeployError(
            f"`{' '.join(command)}` exited {result.returncode}: {message}"
        )
    return result


def fetch_github_json(
    url: str, token: str | None = None, timeout: float = 20
) -> Mapping[str, object]:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace").strip().splitlines()
        detail = body[0] if body else ""
        raise DeployError(f"GitHub API returned {exc.code} for {url}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise DeployError(f"could not read {url}: {exc}") from exc


def service_is_healthy(url: str) -> bool:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return 200 <= response.status < 300
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def ci_state(
    payload: Mapping[str, object], sha: str, branch: str
) -> str:
    """Reduce an Actions runs response to the one fact that matters.

    A matching run must be a `push` on the same branch and the same commit.
    Pull-request runs, workflow dispatches and runs for an older commit are
    ignored; only `success` allows a deploy.
    """
    runs = payload.get("workflow_runs")
    if not isinstance(runs, list):
        return "missing"
    matching = [
        run
        for run in runs
        if isinstance(run, Mapping)
        and run.get("head_sha") == sha
        and run.get("head_branch") == branch
        and run.get("event") == "push"
    ]
    if not matching:
        return "missing"

    run = max(matching, key=lambda item: str(item.get("created_at") or ""))
    if run.get("status") != "completed":
        return "pending"
    if run.get("conclusion") == "success":
        return "success"
    return f"not successful ({run.get('conclusion') or 'unknown'})"


class Deployer:
    def __init__(
        self,
        config: Config,
        *,
        run: Callable[..., subprocess.CompletedProcess[str]] = run_command,
        http_json: Callable[..., Mapping[str, object]] = fetch_github_json,
        health: Callable[[str], bool] = service_is_healthy,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.config = config
        self.run = run
        self.http_json = http_json
        self.health = health
        self.sleep = sleep

    def _git(self, *args: object, check: bool = True) -> subprocess.CompletedProcess[str]:
        return self.run(
            ["git", *args], cwd=self.config.checkout, check=check
        )

    def _token(self) -> str | None:
        if self.config.token_file is None:
            return None
        try:
            token = self.config.token_file.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise DeployError(
                f"cannot read DEPLOY_GITHUB_TOKEN_FILE {self.config.token_file}: {exc}"
            ) from exc
        return token or None

    def current_sha(self) -> str:
        return self._git("rev-parse", "HEAD").stdout.strip()

    def remote_sha(self) -> str:
        result = self._git(
            "ls-remote", self.config.git_remote, f"refs/heads/{self.config.branch}"
        )
        line = result.stdout.strip()
        if not line:
            raise DeployError(
                f"{self.config.git_remote} has no refs/heads/{self.config.branch}"
            )
        return line.split()[0]

    def ensure_ready(self) -> None:
        inside = self._git("rev-parse", "--git-dir", check=False)
        if inside.returncode != 0:
            raise DeployError(f"{self.config.checkout} is not a git checkout")

        status = self._git("status", "--porcelain").stdout.strip()
        if status:
            raise DeployError(
                "the checkout has local changes; refusing to deploy over them:\n"
                + status
            )

        branch = self._git("symbolic-ref", "--quiet", "--short", "HEAD", check=False)
        current_branch = branch.stdout.strip()
        if branch.returncode != 0 or current_branch != self.config.branch:
            found = current_branch or f"detached HEAD (git exit {branch.returncode})"
            raise DeployError(
                f"checkout is on {found}, expected {self.config.branch}; "
                "check it out by hand before enabling the timer"
            )

    def ci_state_for(self, sha: str) -> str:
        workflow = urllib.parse.quote(self.config.workflow, safe="")
        branch = urllib.parse.quote(self.config.branch, safe="")
        url = (
            f"{GITHUB_API}/repos/{self.config.repo}/actions/workflows/"
            f"{workflow}/runs?branch={branch}&event=push&per_page=20"
        )
        payload = self.http_json(url, token=self._token())
        return ci_state(payload, sha, self.config.branch)

    def _state_path(self) -> Path:
        return self.config.state_file or (
            self.config.checkout / ".git" / "marea-deploy.state"
        )

    def deployed_sha(self) -> str | None:
        path = self._state_path()
        try:
            value = path.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise DeployError(f"cannot read deploy state {path}: {exc}") from exc
        if not value:
            return None
        if not re.fullmatch(r"[0-9a-f]{40,64}", value):
            raise DeployError(
                f"deploy state {path} does not contain a commit SHA; "
                "inspect it and remove it"
            )
        return value

    def _remember(self, sha: str) -> None:
        path = self._state_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_name(path.name + ".tmp")
            temporary.write_text(f"{sha}\n", encoding="utf-8")
            temporary.replace(path)
        except OSError as exc:
            raise DeployError(f"cannot write deploy state {path}: {exc}") from exc

    def _run_release(self, target: str, previous: str | None) -> None:
        try:
            self._install_backend()
            self._build_frontend()
            self._restart()
            self._wait_for_health()
        except Exception as exc:
            LOG.error("deploy of %s failed: %s", target[:12], exc)
            if previous is None:
                raise
            if self._rollback(previous):
                try:
                    self._remember(previous)
                except DeployError as state_error:
                    LOG.error("%s", state_error)
                LOG.error(
                    "rolled back to %s; the failed commit was not deployed",
                    previous[:12],
                )
            else:
                raise DeployError(
                    f"deploy failed and rollback to {previous[:12]} also failed; "
                    "the site needs a human"
                ) from exc
            raise

        self._remember(target)
        LOG.info("deployed %s", target[:12])

    def _fast_forward(self, current: str, remote: str) -> str | None:
        state = self.ci_state_for(remote)
        if state != "success":
            LOG.info("CI for %s is %s; not deploying yet", remote[:12], state)
            return None

        self._git("fetch", "--prune", self.config.git_remote, self.config.branch)
        fetched = self._git(
            "rev-parse", f"{self.config.git_remote}/{self.config.branch}"
        ).stdout.strip()
        if fetched != remote:
            LOG.info(
                "%s moved to %s while checking; the next run will pick it up",
                self.config.branch,
                fetched[:12],
            )
            return None

        ancestor = self._git(
            "merge-base", "--is-ancestor", current, fetched, check=False
        )
        if ancestor.returncode != 0:
            raise DeployError(
                f"{fetched[:12]} is not a fast-forward of {current[:12]}; "
                "the checkout has local commits or was force-pushed and needs a human"
            )
        return fetched

    def deploy(self) -> int:
        self.ensure_ready()
        current = self.current_sha()
        remote = self.remote_sha()
        deployed = self.deployed_sha()

        if remote == current and deployed == current:
            LOG.info("checkout is already deployed at %s", current[:12])
            return 0

        if remote == current:
            # The checkout is at main but the state file is missing or older.
            # A crash between `git merge` and the health check leaves exactly
            # this, so rebuild and restart rather than assuming the running
            # process matches the checkout.
            LOG.warning(
                "checkout is at %s but the last recorded deploy is %s; reconciling",
                current[:12],
                (deployed or "unknown")[:12],
            )
            state = self.ci_state_for(current)
            if state != "success":
                LOG.info("CI for %s is %s; not reconciling yet", current[:12], state)
                return 0
            target = current
            previous = deployed
        else:
            target = self._fast_forward(current, remote)
            if target is None:
                return 0
            previous = deployed if deployed and deployed != current else current
            LOG.info("deploying %s (was %s)", target[:12], current[:12])
            self._git("merge", "--ff-only", target)

        self._run_release(target, previous)
        return 0

    def _install_backend(self) -> None:
        backend = self.config.checkout / "backend"
        pip = backend / "venv" / "bin" / "pip"
        if not pip.exists():
            LOG.info("creating the backend virtualenv")
            self.run(["python3", "-m", "venv", str(backend / "venv")], cwd=backend)
        self.run(
            [
                str(pip),
                "install",
                "--quiet",
                "--disable-pip-version-check",
                "-r",
                "requirements.txt",
            ],
            cwd=backend,
        )

    def _build_frontend(self) -> None:
        frontend = self.config.checkout / "frontend"
        self.run(["npm", "ci", "--no-audit", "--no-fund"], cwd=frontend)
        self.run(["npm", "run", "build"], cwd=frontend)

    def _restart(self) -> None:
        self.run(
            ["sudo", "-n", "systemctl", "restart", self.config.service],
            cwd=self.config.checkout,
        )

    def _wait_for_health(self) -> None:
        attempts = max(
            1, math.ceil(self.config.health_timeout / self.config.health_interval)
        )
        for attempt in range(attempts):
            if self.health(self.config.health_url):
                LOG.info("health check passed")
                return
            if attempt + 1 < attempts:
                self.sleep(self.config.health_interval)
        raise DeployError(
            f"{self.config.health_url} did not return 200 after "
            f"{self.config.health_timeout:g}s"
        )

    def _rollback(self, previous: str) -> bool:
        try:
            LOG.warning("rolling back to %s", previous[:12])
            self._git("reset", "--hard", previous)
            self._install_backend()
            self._build_frontend()
            self._restart()
            self._wait_for_health()
            return True
        except Exception as exc:  # noqa: BLE001 - report every rollback failure
            LOG.error("rollback to %s failed: %s", previous[:12], exc)
            return False


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Deploy the tested main branch from a VPS checkout."
    )
    parser.add_argument(
        "--verbose", action="store_true", help="log command output as well"
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    try:
        config = Config.from_env()
    except DeployError as exc:
        LOG.error("configuration: %s", exc)
        return 2

    try:
        config.lock_file.parent.mkdir(parents=True, exist_ok=True)
        with config.lock_file.open("w") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                LOG.info("another deploy is already running; skipping")
                return 0
            try:
                return Deployer(config).deploy()
            except DeployError as exc:
                LOG.error("%s", exc)
                return 1
    except OSError as exc:
        LOG.error("cannot use lock file %s: %s", config.lock_file, exc)
        return 2


if __name__ == "__main__":
    sys.exit(main())
