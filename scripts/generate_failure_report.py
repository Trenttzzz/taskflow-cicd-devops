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


MODEL = "gemma-4-31b-it"
RETRYABLE_HTTP_CODES = {429, 500, 503, 504}
MAX_GEMMA_ATTEMPTS = 3
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
    excerpt = "\n".join(clean_log.splitlines()[:80]) or "Log tidak tersedia."
    return f"""# AI Failure Intelligence Report

## Status

Laporan fallback dibuat. {reason}

## Failed Stage

{failed_jobs}

## Current Failure Summary

Analisis LLM tidak tersedia. Gunakan cuplikan log dan failure serupa di bawah sebagai bukti awal.

## Most Similar Failures

{similar_lines}

## Likely Root Cause

evidence belum cukup

## Evidence

```text
{excerpt}
```

## OOVD-Inspired Signals

{oovd_lines}

## Suggested Debugging Steps

1. Baca failed step pada GitHub Actions.
2. Jalankan command yang gagal secara lokal bila memungkinkan.
3. Cek artifact scan, coverage, atau log container sesuai failed stage.
4. Perbaiki penyebab yang terlihat di evidence, lalu ulangi pipeline.

## Notes and Limits

Report ini tidak memanggil Gemma karena fallback aktif.
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
{clean_log[:12000]}
```

Similar failures:
{json.dumps(similar.get("top_k", []), indent=2)}

OOVD-inspired suspicious lines:
{json.dumps(oovd.get("items", [])[:10], indent=2)}

Knowledge base notes:
{json.dumps(notes, indent=2)}
"""


def call_gemma(api_key, prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 2048},
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        method="POST",
    )
    for attempt in range(1, MAX_GEMMA_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                data = json.loads(response.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as error:
            if error.code not in RETRYABLE_HTTP_CODES or attempt == MAX_GEMMA_ATTEMPTS:
                raise
            wait_seconds = attempt * 3
            print(f"Gemma API mengembalikan HTTP {error.code}. Retry {attempt}/{MAX_GEMMA_ATTEMPTS} dalam {wait_seconds} detik.")
            time.sleep(wait_seconds)

    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    text = "\n".join(part.get("text", "") for part in parts).strip()
    if not text:
        raise ValueError("Gemma response did not include text.")
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
        print("Pipeline sukses. Embedding API dan Gemma API tidak dipanggil.")
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
        report = call_gemma(api_key, prompt)
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, json.JSONDecodeError, TimeoutError, ValueError) as error:
        error_reason = type(error).__name__
        if isinstance(error, urllib.error.HTTPError):
            error_reason = f"HTTP {error.code}"
        REPORT_FILE.write_text(
            fallback_report(status, clean_log, similar, oovd, f"Gemma API gagal: {error_reason}."),
            encoding="utf-8",
        )
        print("Laporan fallback dibuat setelah Gemma API gagal.")
        return

    REPORT_FILE.write_text(normalize_report(mask_secrets(report)).rstrip() + "\n", encoding="utf-8")
    print("Report AI failure berhasil dibuat.")


if __name__ == "__main__":
    main()
