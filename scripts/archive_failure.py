#!/usr/bin/env python3
"""Arsipkan cleaned failure log sebagai history provisional."""

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

try:
    from clean_failure_log import mask_secrets
except ModuleNotFoundError:
    from scripts.clean_failure_log import mask_secrets


class ArchiveError(Exception):
    """Error input atau penyimpanan failure archive."""


def read_json(path, label, default=None):
    if not path.exists():
        if default is not None:
            return default
        raise ArchiveError(f"{label} tidak tersedia.")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ArchiveError(f"{label} tidak valid.") from error


def write_json_atomic(path, payload):
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary_path.replace(path)


# Abaikan URL run dinamis saat menghitung duplicate content.
def content_hash(sanitized_log):
    stable_lines = [
        line
        for line in sanitized_log.splitlines()
        if not line.strip().lower().startswith("html_url:")
    ]
    stable_text = "\n".join(stable_lines).strip() + "\n"
    return hashlib.sha256(stable_text.encode("utf-8")).hexdigest()


# Buat entry provisional tanpa mempercayai diagnosis AI.
def archive_failure(archive_dir, clean_log_path, status_path, similar_path, provenance):
    required_provenance = {"run_id", "run_attempt", "commit_sha", "repository", "run_url"}
    missing = sorted(key for key in required_provenance if not str(provenance.get(key, "")).strip())
    if missing:
        raise ArchiveError(f"Provenance tidak lengkap: {', '.join(missing)}.")

    status = read_json(status_path, "Status failure")
    if not isinstance(status, dict):
        raise ArchiveError("Status failure tidak memiliki struktur yang valid.")
    if status.get("should_analyze") is not True:
        raise ArchiveError("Archive hanya dibuat untuk pipeline failure.")

    failed_jobs = status.get("failed_jobs")
    if not isinstance(failed_jobs, list) or not all(isinstance(job, str) and job.strip() for job in failed_jobs):
        raise ArchiveError("Daftar failed jobs tidak valid.")

    if not clean_log_path.exists():
        raise ArchiveError("Cleaned failure log tidak tersedia.")
    sanitized_log = mask_secrets(clean_log_path.read_text(encoding="utf-8", errors="replace")).strip()
    if not sanitized_log:
        raise ArchiveError("Cleaned failure log kosong.")
    sanitized_log += "\n"

    run_id = str(provenance["run_id"]).strip()
    run_attempt = str(provenance["run_attempt"]).strip()
    if not re.fullmatch(r"[0-9]+", run_id) or not re.fullmatch(r"[0-9]+", run_attempt):
        raise ArchiveError("Run ID dan run attempt harus berupa angka.")

    archive_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = archive_dir / "metadata.json"
    metadata = read_json(metadata_path, "Archive metadata", {"version": 1, "entries": []})
    if not isinstance(metadata, dict) or metadata.get("version") != 1 or not isinstance(metadata.get("entries"), list):
        raise ArchiveError("Archive metadata tidak memiliki struktur yang valid.")

    content_sha256 = content_hash(sanitized_log)
    if any(entry.get("content_sha256") == content_sha256 for entry in metadata["entries"]):
        return "duplicate"

    entry_id = f"real-{run_id}-attempt-{run_attempt}"
    if any(entry.get("id") == entry_id for entry in metadata["entries"]):
        raise ArchiveError(f"Archive ID {entry_id} sudah ada dengan log berbeda.")

    log_relative_path = Path("real-logs") / f"{entry_id}.cleaned.log"
    note_relative_path = Path("notes") / f"{entry_id}.md"
    log_path = archive_dir / log_relative_path
    note_path = archive_dir / note_relative_path
    log_path.parent.mkdir(parents=True, exist_ok=True)
    note_path.parent.mkdir(parents=True, exist_ok=True)

    similar = read_json(similar_path, "Similar failures", {"top_k": []})
    top_k = similar.get("top_k", []) if isinstance(similar, dict) else []
    if not isinstance(top_k, list):
        top_k = []
    candidate_lines = []
    for candidate in top_k[:3]:
        if not isinstance(candidate, dict):
            continue
        candidate_lines.append(
            f"- Rank {candidate.get('rank', '?')}: {candidate.get('id', 'unknown')} "
            f"({candidate.get('category', 'unknown')}), similarity {candidate.get('similarity', 'unknown')}"
        )
    if not candidate_lines:
        candidate_lines.append("- Tidak tersedia.")

    entry = {
        "id": entry_id,
        "source_type": "real",
        "run_id": run_id,
        "run_attempt": run_attempt,
        "commit_sha": str(provenance["commit_sha"]).strip(),
        "repository": str(provenance["repository"]).strip(),
        "run_url": str(provenance["run_url"]).strip(),
        "failed_jobs": [job.strip() for job in failed_jobs],
        "category": "unclassified",
        "log_file": log_relative_path.as_posix(),
        "note_file": note_relative_path.as_posix(),
        "content_sha256": content_sha256,
        "validated": False,
        "root_cause": "Menunggu validasi.",
        "resolution": "Menunggu validasi.",
    }
    note = f"""# Provisional Failure {entry_id}

## Provenance

- Repository: `{entry["repository"]}`
- Run: [{run_id} attempt {run_attempt}]({entry["run_url"]})
- Commit: `{entry["commit_sha"]}`
- Failed jobs: `{", ".join(entry["failed_jobs"])}`
- Content SHA-256: `{content_sha256}`

## Similar Failure Candidates

{chr(10).join(candidate_lines)}

## Validation

Entry ini belum tervalidasi. Isi category, root cause, dan resolution berdasarkan
perbaikan nyata sebelum mengubah `validated` menjadi `true`.
"""

    log_path.write_text(sanitized_log, encoding="utf-8")
    note_path.write_text(note, encoding="utf-8")
    metadata["entries"].append(entry)
    write_json_atomic(metadata_path, metadata)
    return "created"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive-dir", default="failure-history")
    parser.add_argument("--clean-log", default="ai-reports/current-failure.cleaned.log")
    parser.add_argument("--status", default="ai-reports/status.json")
    parser.add_argument("--similar", default="ai-reports/similar-failures.json")
    args = parser.parse_args()

    repository = os.environ.get("GITHUB_REPOSITORY", "").strip()
    server_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
    run_id = os.environ.get("GITHUB_RUN_ID", "").strip()
    provenance = {
        "run_id": run_id,
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", "").strip(),
        "commit_sha": os.environ.get("GITHUB_SHA", "").strip(),
        "repository": repository,
        "run_url": f"{server_url}/{repository}/actions/runs/{run_id}",
    }

    try:
        result = archive_failure(
            Path(args.archive_dir),
            Path(args.clean_log),
            Path(args.status),
            Path(args.similar),
            provenance,
        )
    except ArchiveError as error:
        print(f"Failure archive gagal: {error}", file=sys.stderr)
        return 1

    print("Failure archive dibuat." if result == "created" else "Failure archive duplikat; tidak ada perubahan.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
