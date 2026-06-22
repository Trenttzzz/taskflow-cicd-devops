#!/usr/bin/env python3
"""Ambil log failed job dari current GitHub Actions run."""

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path


REPORT_DIR = Path("ai-reports")
RAW_LOG_FILE = REPORT_DIR / "current-failure.log"
FAILED_CONCLUSIONS = {"failure", "cancelled", "timed_out", "action_required"}
MAX_ATTEMPTS = 6


def github_request(url, token, accept="application/vnd.github+json"):
    request = urllib.request.Request(
        url,
        headers={
            "Accept": accept,
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def list_run_jobs(repository, run_id, token):
    jobs = []
    page = 1
    while True:
        url = f"https://api.github.com/repos/{repository}/actions/runs/{run_id}/jobs?per_page=100&page={page}"
        data = json.loads(github_request(url, token).decode("utf-8"))
        page_jobs = data.get("jobs", [])
        jobs.extend(page_jobs)
        if len(page_jobs) < 100:
            return jobs
        page += 1


def download_job_log(repository, job_id, token):
    url = f"https://api.github.com/repos/{repository}/actions/jobs/{job_id}/logs"
    return github_request(url, token, "application/vnd.github+json").decode("utf-8", errors="replace")


def format_job_header(job):
    return "\n".join(
        [
            f"===== Failed job: {job.get('name', 'unknown')} =====",
            f"status: {job.get('status', 'unknown')}",
            f"conclusion: {job.get('conclusion', 'unknown')}",
            f"html_url: {job.get('html_url', 'unknown')}",
            "",
        ]
    )


def collect_failed_logs(repository, run_id, token):
    jobs = list_run_jobs(repository, run_id, token)
    failed_jobs = [job for job in jobs if job.get("conclusion") in FAILED_CONCLUSIONS]
    if not failed_jobs:
        return "No failed job logs were available yet.\n"

    chunks = []
    for job in failed_jobs:
        chunks.append(format_job_header(job))
        try:
            chunks.append(download_job_log(repository, job["id"], token).strip())
        except (KeyError, urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as error:
            chunks.append(f"Log download failed for job {job.get('name', 'unknown')}: {type(error).__name__}.")
        chunks.append("")
    return "\n".join(chunks).strip() + "\n"


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    repository = os.environ.get("GITHUB_REPOSITORY", "").strip()
    run_id = os.environ.get("GITHUB_RUN_ID", "").strip()
    token = os.environ.get("GITHUB_TOKEN", "").strip()

    if not token:
        RAW_LOG_FILE.write_text("Log collection failed: GITHUB_TOKEN is missing.\n", encoding="utf-8")
        return
    if not repository or not run_id:
        RAW_LOG_FILE.write_text("Log collection failed: GITHUB_REPOSITORY or GITHUB_RUN_ID is missing.\n", encoding="utf-8")
        return

    last_error = ""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            output = collect_failed_logs(repository, run_id, token)
            if "No failed job logs were available yet." not in output:
                RAW_LOG_FILE.write_text(output, encoding="utf-8")
                return
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as error:
            last_error = type(error).__name__
        if attempt < MAX_ATTEMPTS:
            time.sleep(attempt * 3)

    message = "Log collection failed: failed job logs were not available from GitHub Jobs API."
    if last_error:
        message = f"{message} Last error: {last_error}."
    RAW_LOG_FILE.write_text(message + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
