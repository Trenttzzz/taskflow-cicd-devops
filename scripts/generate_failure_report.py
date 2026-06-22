#!/usr/bin/env python3
"""Buat report AI Failure Intelligence."""

import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

try:
    from env_loader import load_dotenv
except ModuleNotFoundError:
    from scripts.env_loader import load_dotenv


MODEL = "gemini-3.1-flash-lite"
RETRYABLE_HTTP_CODES = {429, 500, 503, 504}
MAX_LLM_ATTEMPTS = 5
LLM_TIMEOUT_SECONDS = 180
REPORT_DIR = Path("ai-reports")
STATUS_FILE = REPORT_DIR / "status.json"
CLEAN_LOG_FILE = REPORT_DIR / "current-failure.cleaned.log"
SIMILAR_FILE = REPORT_DIR / "similar-failures.json"
OOVD_FILE = REPORT_DIR / "oovd-lines.json"
REPORT_FILE = REPORT_DIR / "failure-intelligence-report.md"


def read_json(path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def read_text(path, default=""):
    if not path.exists():
        return default
    return path.read_text(encoding="utf-8", errors="replace")


def mask_secrets(text):
    patterns = [
        r"ghp_[A-Za-z0-9_]{20,}",
        r"github_pat_[A-Za-z0-9_]{20,}",
        r"AIza[A-Za-z0-9_\-]{20,}",
        r"Bearer\s+[A-Za-z0-9._\-]+",
        r"(password=)[^\s&]+",
        r"(token=)[^\s&]+",
    ]
    masked = text
    for pattern in patterns:
        if pattern.startswith("(password=") or pattern.startswith("(token="):
            masked = re.sub(pattern, r"\1[MASKED]", masked, flags=re.IGNORECASE)
        else:
            masked = re.sub(pattern, "[MASKED]", masked, flags=re.IGNORECASE)
    return masked


def load_similar_notes(similar):
    notes = []
    for entry in similar.get("top_k", []):
        note_path = Path(entry.get("note_file", ""))
        notes.append(
            {
                "id": entry.get("id"),
                "category": entry.get("category"),
                "similarity": entry.get("similarity"),
                "note": read_text(note_path, "Note unavailable."),
            }
        )
    return notes


def compact_failure_log(clean_log):
    patterns = [
        r"failed job",
        r"coverage",
        r"total:",
        r"total coverage",
        r"is below",
        r"exit code",
        r"error",
        r"panic",
        r"timeout",
        r"gosec",
        r"govulncheck",
        r"health",
        r"stats",
    ]
    important = []
    seen = set()
    for line in clean_log.splitlines():
        normalized = line.strip()
        if not normalized:
            continue
        if not any(re.search(pattern, normalized, re.IGNORECASE) for pattern in patterns):
            continue
        if normalized in seen:
            continue
        important.append(normalized)
        seen.add(normalized)
    if not important:
        important = clean_log.splitlines()[:120]
    return "\n".join(important[:160])


def infer_root_cause(clean_log):
    coverage_match = re.search(r"Coverage\s+([0-9.]+)%\s+is below\s+([0-9.]+)%", clean_log, re.IGNORECASE)
    if coverage_match:
        current, threshold = coverage_match.groups()
        return (
            f"Pipeline gagal karena total coverage {current}% berada di bawah threshold {threshold}%.",
            [
                f"Coverage {current}% is below {threshold}%",
                f"Total coverage: {current}%",
            ],
            [
                "Jalankan `go test ./... -coverprofile=coverage.out -covermode=atomic` secara lokal.",
                "Buka `go tool cover -func=coverage.out` untuk melihat package atau function dengan coverage rendah.",
                "Tambahkan unit test pada branch logic yang belum tercakup, lalu push ulang setelah coverage melewati threshold.",
            ],
        )
    if re.search(r"gosec|govulncheck|vulnerability", clean_log, re.IGNORECASE):
        return (
            "Pipeline gagal karena security scan menemukan finding blocking.",
            ["Security scan menemukan finding pada log pipeline."],
            [
                "Buka artifact `gosec-report.json` atau `govulncheck-report.json`.",
                "Perbaiki dependency vulnerable atau code pattern yang ditandai.",
                "Jalankan ulang security scan sebelum push ulang.",
            ],
        )
    if re.search(r"health|stats|curl", clean_log, re.IGNORECASE):
        return (
            "Pipeline gagal pada smoke test aplikasi.",
            ["Smoke test endpoint health atau stats gagal."],
            [
                "Cek `docker logs taskflow-api` pada job CD.",
                "Pastikan aplikasi bind ke port 8080 dan `DATABASE_URL` benar.",
                "Uji `/health` dan `/api/v1/stats` secara lokal.",
            ],
        )
    return (
        "evidence belum cukup",
        [],
        [
            "Baca failed step pada GitHub Actions.",
            "Jalankan command yang gagal secara lokal bila memungkinkan.",
            "Cek artifact scan, coverage, atau log container sesuai failed stage.",
            "Perbaiki penyebab yang terlihat di evidence, lalu ulangi pipeline.",
        ],
    )


def fallback_report(status, clean_log, similar, oovd, reason):
    top_k = similar.get("top_k", [])
    similar_lines = "\n".join(
        f"- {item.get('id')} ({item.get('category')}), kemiripan {item.get('similarity')}"
        for item in top_k
    ) or "- Tidak tersedia."
    oovd_lines = "\n".join(
        f"- score {item.get('score')}: {item.get('line')}"
        for item in oovd.get("items", [])[:5]
    ) or "- Tidak tersedia."
    failed_jobs = ", ".join(status.get("failed_jobs", [])) or "Tidak diketahui."
    summary, evidence_lines, steps = infer_root_cause(clean_log)
    evidence = "\n".join(f"- {line}" for line in evidence_lines) or f"```text\n{compact_failure_log(clean_log)}\n```"
    step_lines = "\n".join(f"{index}. {step}" for index, step in enumerate(steps, start=1))
    return f"""# AI Failure Intelligence Report

## Status

Laporan fallback dibuat. {reason}

## Failed Stage

{failed_jobs}

## Current Failure Summary

{summary}

## Most Similar Failures

{similar_lines}

## Likely Root Cause

{summary}

## Evidence

{evidence}

## OOVD-Inspired Signals

{oovd_lines}

## Suggested Debugging Steps

{step_lines}

## Notes and Limits

Report ini tidak memanggil LLM karena fallback aktif.
"""


def build_prompt(status, clean_log, similar, notes, oovd):
    return f"""Tulis seluruh narasi dalam Bahasa Indonesia yang natural.
Istilah teknis boleh tetap dalam English jika itu nama command, endpoint, job, model, file, error, field JSON, atau istilah umum seperti coverage, smoke test, root cause, dan debugging.
Jangan menulis paragraf pembuka, checklist validasi, atau mengulang instruksi prompt.
Jangan membuat root cause di luar bukti log.
Jika bukti belum cukup, tulis persis: "evidence belum cukup".
Jangan menampilkan secret.
Sertakan top-3 similar failures.
Sertakan langkah debugging yang bisa dijalankan.
Jangan menyarankan GKE atau Kubernetes.

Buat hanya Markdown final dengan bagian berikut:
# AI Failure Intelligence Report
## Status
## Failed Stage
## Current Failure Summary
## Most Similar Failures
## Likely Root Cause
## Evidence
## Suggested Debugging Steps
## Notes and Limits

Status pipeline:
{json.dumps(status, indent=2)}

Current cleaned failure log:
```text
{compact_failure_log(clean_log)[:6000]}
```

Similar failures:
{json.dumps(similar.get("top_k", []), indent=2)}

OOVD-inspired suspicious lines:
{json.dumps(oovd.get("items", [])[:10], indent=2)}

Knowledge base notes:
{json.dumps(notes, indent=2)}
"""


def call_llm(api_key, prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1200},
    }
    last_error = None
    for attempt in range(1, MAX_LLM_ATTEMPTS + 1):
        try:
            request = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=LLM_TIMEOUT_SECONDS) as response:
                data = json.loads(response.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as error:
            last_error = error
            if error.code not in RETRYABLE_HTTP_CODES or attempt == MAX_LLM_ATTEMPTS:
                raise
            wait_seconds = attempt * 10
            print(f"LLM API mengembalikan HTTP {error.code}. Retry {attempt}/{MAX_LLM_ATTEMPTS} dalam {wait_seconds} detik.")
            time.sleep(wait_seconds)
        except (urllib.error.URLError, TimeoutError) as error:
            last_error = error
            if attempt == MAX_LLM_ATTEMPTS:
                raise
            wait_seconds = attempt * 10
            print(f"LLM API timeout/network error. Retry {attempt}/{MAX_LLM_ATTEMPTS} dalam {wait_seconds} detik.")
            time.sleep(wait_seconds)
    else:
        raise last_error or TimeoutError("LLM API request failed.")

    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    text = "\n".join(part.get("text", "") for part in parts).strip()
    if not text:
        raise ValueError("LLM response did not include text.")
    return text


def normalize_report(text):
    header_match = re.search(r"(?m)^# AI Failure Intelligence Report\s*$", text)
    if not header_match:
        return text
    return text[header_match.start() :]


def main():
    load_dotenv()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    status = read_json(STATUS_FILE, {"should_analyze": True, "failed_jobs": ["unknown"]})
    clean_log = mask_secrets(read_text(CLEAN_LOG_FILE, "No cleaned failure log available."))
    similar = read_json(SIMILAR_FILE, {"top_k": [], "error": "Similar failures unavailable."})
    oovd = read_json(OOVD_FILE, {"items": []})

    if not status.get("should_analyze", True):
        success_file = REPORT_DIR / "success-status.txt"
        success_file.write_text("Pipeline succeeded. No AI failure analysis needed.\n", encoding="utf-8")
        if REPORT_FILE.exists():
            REPORT_FILE.unlink()
        print("Pipeline sukses. Embedding API dan LLM API tidak dipanggil.")
        return

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        REPORT_FILE.write_text(
            fallback_report(status, clean_log, similar, oovd, "GEMINI_API_KEY tidak tersedia."),
            encoding="utf-8",
        )
        print("Laporan fallback dibuat tanpa GEMINI_API_KEY.")
        return

    prompt = build_prompt(status, clean_log, similar, load_similar_notes(similar), oovd)
    try:
        report = call_llm(api_key, prompt)
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, json.JSONDecodeError, TimeoutError, ValueError) as error:
        error_reason = type(error).__name__
        if isinstance(error, urllib.error.HTTPError):
            error_reason = f"HTTP {error.code}"
        REPORT_FILE.write_text(
            fallback_report(status, clean_log, similar, oovd, f"LLM API gagal: {error_reason}."),
            encoding="utf-8",
        )
        print("Laporan fallback dibuat setelah LLM API gagal.")
        return

    REPORT_FILE.write_text(normalize_report(mask_secrets(report)).rstrip() + "\n", encoding="utf-8")
    print("Report AI failure berhasil dibuat.")


if __name__ == "__main__":
    main()
