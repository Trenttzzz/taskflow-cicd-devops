#!/usr/bin/env python3
"""Bersihkan log failure sebelum retrieval dan prompt."""

import argparse
import json
import re
from pathlib import Path


ANSI_PATTERN = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z\s*")
SECRET_PATTERNS = [
    re.compile(r"ghp_[A-Za-z0-9_]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"AIza[A-Za-z0-9_\-]{20,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._\-]+", re.IGNORECASE),
    re.compile(r"(password=)[^\s&]+", re.IGNORECASE),
    re.compile(r"(token=)[^\s&]+", re.IGNORECASE),
]
IMPORTANT_PATTERN = re.compile(
    r"(error|failed|failure|panic|timeout|deadline|refused|exit code|coverage|vulnerability|gosec|govulncheck|curl|health|stats)",
    re.IGNORECASE,
)
TOKEN_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9_.:/-]*")
NORMAL_CI_VOCAB = {
    "actions",
    "api",
    "app",
    "artifact",
    "bin",
    "branch",
    "build",
    "cache",
    "checkout",
    "ci",
    "cmd",
    "commit",
    "container",
    "coverage",
    "curl",
    "database",
    "docker",
    "done",
    "download",
    "env",
    "error",
    "exit",
    "file",
    "go",
    "github",
    "health",
    "image",
    "install",
    "job",
    "json",
    "localhost",
    "log",
    "main",
    "module",
    "ok",
    "package",
    "path",
    "postgres",
    "pull",
    "push",
    "run",
    "runner",
    "script",
    "server",
    "service",
    "setup",
    "sha",
    "stats",
    "step",
    "taskflow",
    "test",
    "timeout",
    "total",
    "ubuntu",
    "upload",
    "with",
    "workflow",
}


def mask_secrets(line):
    masked = line
    for pattern in SECRET_PATTERNS:
        if pattern.pattern.startswith("(password=") or pattern.pattern.startswith("(token="):
            masked = pattern.sub(r"\1[MASKED]", masked)
        else:
            masked = pattern.sub("[MASKED]", masked)
    return masked


def token_root(token):
    return token.lower().strip(".,;:()[]{}'\"`")


def is_dynamic_token(token):
    value = token_root(token)
    if len(value) <= 2:
        return True
    if value in NORMAL_CI_VOCAB:
        return True
    if value.startswith(("http://", "https://", "sha-", "refs/", "github.com/")):
        return True
    if re.fullmatch(r"[a-f0-9]{7,64}", value):
        return True
    if re.fullmatch(r"\d+(?:\.\d+)?%?", value):
        return True
    if "/" in value and not value.endswith((".go", ".sql", ".mod", ".sum")):
        return True
    return False


# Tandai baris yang berbeda dari vocabulary CI umum.
def score_oov_line(line):
    tokens = [token_root(token) for token in TOKEN_PATTERN.findall(line)]
    oov_tokens = []
    for token in tokens:
        if is_dynamic_token(token):
            continue
        if any(part in NORMAL_CI_VOCAB for part in re.split(r"[-_./:]", token)):
            continue
        oov_tokens.append(token)
    return sorted(set(oov_tokens))


def collect_oovd_lines(lines, max_items):
    scored = []
    for index, line in enumerate(lines, start=1):
        tokens = score_oov_line(line)
        if len(tokens) <= 1:
            continue
        scored.append(
            {
                "line_number": index,
                "score": len(tokens),
                "tokens": tokens[:12],
                "line": line,
            }
        )
    scored.sort(key=lambda item: (item["score"], item["line_number"]), reverse=True)
    return list(reversed(scored[:max_items]))


def clean_lines(raw_text, max_lines):
    cleaned = []
    for raw_line in raw_text.splitlines():
        line = ANSI_PATTERN.sub("", raw_line)
        line = TIMESTAMP_PATTERN.sub("", line).rstrip()
        line = mask_secrets(line)
        if line:
            cleaned.append(line)

    if len(cleaned) <= max_lines:
        return cleaned

    oovd = [item["line"] for item in collect_oovd_lines(cleaned, max_lines)]
    important = [line for line in cleaned if IMPORTANT_PATTERN.search(line)]
    focused = []
    seen = set()
    for line in important + oovd:
        if line in seen:
            continue
        focused.append(line)
        seen.add(line)
    if len(focused) >= max_lines:
        return focused[-max_lines:]

    remaining_slots = max_lines - len(focused)
    return cleaned[-remaining_slots:] + focused


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="ai-reports/current-failure.log")
    parser.add_argument("--output", default="ai-reports/current-failure.cleaned.log")
    parser.add_argument("--oov-output", default="ai-reports/oovd-lines.json")
    parser.add_argument("--max-lines", type=int, default=400)
    parser.add_argument("--max-oov-lines", type=int, default=40)
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    raw_text = input_path.read_text(encoding="utf-8", errors="replace") if input_path.exists() else ""
    if not raw_text.strip():
        raw_text = "No failure log was collected."

    cleaned_lines = clean_lines(raw_text, args.max_lines)
    output_path.write_text("\n".join(cleaned_lines) + "\n", encoding="utf-8")

    oov_path = Path(args.oov_output)
    oov_path.parent.mkdir(parents=True, exist_ok=True)
    oov_payload = {
        "description": "OOVD-inspired lines based on uncommon CI log tokens, not a trained OOVD model.",
        "items": collect_oovd_lines(cleaned_lines, args.max_oov_lines),
    }
    oov_path.write_text(json.dumps(oov_payload, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
