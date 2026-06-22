#!/usr/bin/env python3
"""Tentukan apakah analisis AI perlu berjalan."""

import json
import os
from pathlib import Path


REPORT_DIR = Path("ai-reports")
STATUS_FILE = REPORT_DIR / "status.json"
KNOWN_SUCCESS = {"success", "skipped"}
KNOWN_FAILURE = {"failure", "cancelled", "timed_out", "action_required"}
JOB_ENV_KEYS = {
    "ci": "CI_RESULT",
    "security": "SECURITY_RESULT",
    "cd": "CD_RESULT",
    "tag-stable": "TAG_STABLE_RESULT",
}


# Tulis output untuk GitHub Actions dan script lokal.
def write_github_output(name, value):
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with open(output_path, "a", encoding="utf-8") as output_file:
        output_file.write(f"{name}={value}\n")


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    results = {
        job_name: os.environ.get(env_key, "unknown").strip().lower()
        for job_name, env_key in JOB_ENV_KEYS.items()
    }

    failed_jobs = []
    unknown_jobs = []
    for job_name, result in results.items():
        if result in KNOWN_SUCCESS:
            continue
        if result in KNOWN_FAILURE:
            failed_jobs.append(job_name)
            continue
        unknown_jobs.append(job_name)

    should_analyze = bool(failed_jobs or unknown_jobs)
    summary = (
        "Pipeline failed. AI failure analysis required."
        if should_analyze
        else "Pipeline succeeded. No AI failure analysis needed."
    )
    status = {
        "should_analyze": should_analyze,
        "summary": summary,
        "job_results": results,
        "failed_jobs": failed_jobs + unknown_jobs,
    }
    STATUS_FILE.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    write_github_output("should_analyze", str(should_analyze).lower())
    print(summary)


if __name__ == "__main__":
    main()
