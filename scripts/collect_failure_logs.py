#!/usr/bin/env python3
"""Ambil log failed job dari current GitHub Actions run."""

import os
import shutil
import subprocess
from pathlib import Path


REPORT_DIR = Path("ai-reports")
RAW_LOG_FILE = REPORT_DIR / "current-failure.log"


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    gh_path = shutil.which("gh")
    repository = os.environ.get("GITHUB_REPOSITORY", "").strip()
    run_id = os.environ.get("GITHUB_RUN_ID", "").strip()

    if not gh_path:
        RAW_LOG_FILE.write_text("Log collection failed: GitHub CLI is not available.\n", encoding="utf-8")
        return
    if not repository or not run_id:
        RAW_LOG_FILE.write_text("Log collection failed: GITHUB_REPOSITORY or GITHUB_RUN_ID is missing.\n", encoding="utf-8")
        return

    command = [gh_path, "run", "view", run_id, "--repo", repository, "--log-failed"]
    env = os.environ.copy()
    token = env.get("GITHUB_TOKEN") or env.get("GH_TOKEN")
    if token:
        env["GH_TOKEN"] = token

    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True, env=env, timeout=120)
    except (OSError, subprocess.SubprocessError) as error:
        RAW_LOG_FILE.write_text(f"Log collection failed: {type(error).__name__}.\n", encoding="utf-8")
        return

    output = result.stdout.strip() or result.stderr.strip()
    if result.returncode != 0:
        output = f"Log collection failed with exit code {result.returncode}.\n{output}\n"
    RAW_LOG_FILE.write_text(output + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
