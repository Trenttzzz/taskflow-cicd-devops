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
HISTORY_DIR = Path(os.environ.get("FAILURE_HISTORY_DIR", "failure-history"))


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_document_text(entry, base_dir):
    log_text = (base_dir / entry["log_file"]).read_text(encoding="utf-8", errors="replace")
    note_text = (base_dir / entry["note_file"]).read_text(encoding="utf-8", errors="replace")
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


def load_validated_history_entries(history_dir):
    metadata_path = history_dir / "metadata.json"
    if not metadata_path.exists():
        return []

    metadata = read_json(metadata_path)
    entries = []
    for entry in metadata.get("entries", []):
        if entry.get("source_type") != "real" or entry.get("validated") is not True:
            continue
        required_text = ("id", "category", "log_file", "note_file", "root_cause", "resolution")
        if not all(isinstance(entry.get(key), str) and entry[key].strip() for key in required_text):
            continue
        if entry["category"] == "unclassified":
            continue
        if entry["root_cause"] == "Menunggu validasi." or entry["resolution"] == "Menunggu validasi.":
            continue
        if not (history_dir / entry["log_file"]).is_file() or not (history_dir / entry["note_file"]).is_file():
            continue
        entries.append((entry, history_dir))
    return entries


def main():
    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("GEMINI_API_KEY is not set. Embedding index was not generated.")
        return 0

    metadata = read_json(METADATA_FILE)
    source_entries = [(entry, KB_DIR) for entry in metadata["entries"]]
    try:
        source_entries.extend(load_validated_history_entries(HISTORY_DIR))
    except (OSError, json.JSONDecodeError) as error:
        print(f"Failure history metadata tidak valid: {type(error).__name__}")
        return 0

    existing_entries = load_existing_entries()
    index_entries = []
    indexed_ids = set()

    for entry, base_dir in source_entries:
        if entry["id"] in indexed_ids:
            print(f"Duplicate knowledge base ID dilewati: {entry['id']}")
            continue
        indexed_ids.add(entry["id"])
        document_text = build_document_text(entry, base_dir)
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
                "note_file": str(base_dir / entry["note_file"]),
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
