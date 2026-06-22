#!/usr/bin/env python3
"""Bangun embedding index knowledge base dengan Gemini API."""

import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

try:
    from env_loader import load_dotenv
except ModuleNotFoundError:
    from scripts.env_loader import load_dotenv


MODEL = "gemini-embedding-2"
OUTPUT_DIMENSIONALITY = 768
KB_DIR = Path("failure-knowledge-base")
METADATA_FILE = KB_DIR / "metadata.json"
INDEX_FILE = KB_DIR / "embeddings" / "embedding-index.json"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_document_text(entry):
    log_text = (KB_DIR / entry["log_file"]).read_text(encoding="utf-8", errors="replace")
    note_text = (KB_DIR / entry["note_file"]).read_text(encoding="utf-8", errors="replace")
    return f"title: {entry['id']} | text: {log_text}\n{entry['root_cause']}\n{entry['resolution']}\n{note_text}"


def embed_text(api_key, text):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:embedContent"
    payload = {
        "content": {"parts": [{"text": text}]},
        "output_dimensionality": OUTPUT_DIMENSIONALITY,
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        data = json.loads(response.read().decode("utf-8"))
    return data["embedding"]["values"]


def load_existing_entries():
    if not INDEX_FILE.exists():
        return {}
    try:
        index = read_json(INDEX_FILE)
    except (OSError, json.JSONDecodeError):
        return {}
    if index.get("model") != MODEL or index.get("output_dimensionality") != OUTPUT_DIMENSIONALITY:
        return {}
    return {entry["id"]: entry for entry in index.get("entries", [])}


def main():
    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("GEMINI_API_KEY is not set. Embedding index was not generated.")
        return 0

    metadata = read_json(METADATA_FILE)
    existing_entries = load_existing_entries()
    index_entries = []

    for entry in metadata["entries"]:
        document_text = build_document_text(entry)
        text_hash = sha256_text(document_text)
        existing = existing_entries.get(entry["id"])
        if existing and existing.get("text_sha256") == text_hash:
            index_entries.append(existing)
            continue

        try:
            embedding = embed_text(api_key, document_text)
        except (urllib.error.URLError, urllib.error.HTTPError, KeyError, json.JSONDecodeError, TimeoutError) as error:
            print(f"Embedding failed for {entry['id']}: {type(error).__name__}")
            return 0

        index_entries.append(
            {
                "id": entry["id"],
                "category": entry["category"],
                "source_type": entry["source_type"],
                "text_sha256": text_hash,
                "embedding": embedding,
                "note_file": str(KB_DIR / entry["note_file"]),
            }
        )

    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    INDEX_FILE.write_text(
        json.dumps(
            {
                "model": MODEL,
                "output_dimensionality": OUTPUT_DIMENSIONALITY,
                "entries": index_entries,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Embedding index contains {len(index_entries)} entries.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
