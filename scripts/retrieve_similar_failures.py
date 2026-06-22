#!/usr/bin/env python3
"""Cari failure knowledge base yang paling mirip."""

import argparse
import json
import math
import os
import urllib.error
import urllib.request
from pathlib import Path

try:
    from env_loader import load_dotenv
except ModuleNotFoundError:
    from scripts.env_loader import load_dotenv


MODEL = "gemini-embedding-2"
OUTPUT_DIMENSIONALITY = 768
INDEX_FILE = Path("failure-knowledge-base/embeddings/embedding-index.json")
OUTPUT_FILE = Path("ai-reports/similar-failures.json")


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


def cosine_similarity(left, right):
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return max(0.0, min(1.0, dot / (left_norm * right_norm)))


def write_output(query_file, top_k, error=None):
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {"query_file": query_file, "top_k": top_k}
    if error:
        payload["error"] = error
    OUTPUT_FILE.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main():
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", default="ai-reports/current-failure.cleaned.log")
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()

    if not INDEX_FILE.exists():
        write_output(args.query, [], "Embedding index is unavailable.")
        return

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        write_output(args.query, [], "GEMINI_API_KEY is not set.")
        return

    index = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    if index.get("model") != MODEL or index.get("output_dimensionality") != OUTPUT_DIMENSIONALITY:
        write_output(args.query, [], "Embedding index model metadata does not match retrieval config.")
        return

    query_text = Path(args.query).read_text(encoding="utf-8", errors="replace")
    query_payload = f"task: search result | query: {query_text}"
    try:
        query_embedding = embed_text(api_key, query_payload)
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, json.JSONDecodeError, TimeoutError) as error:
        write_output(args.query, [], f"Query embedding failed: {type(error).__name__}.")
        return

    ranked = []
    for entry in index.get("entries", []):
        similarity = cosine_similarity(query_embedding, entry.get("embedding", []))
        ranked.append(
            {
                "id": entry["id"],
                "category": entry["category"],
                "source_type": entry["source_type"],
                "similarity": round(similarity, 4),
                "note_file": entry["note_file"],
            }
        )
    ranked.sort(key=lambda item: item["similarity"], reverse=True)

    top_entries = []
    for rank, entry in enumerate(ranked[: args.top_k], start=1):
        top_entries.append({"rank": rank, **entry})
    write_output(args.query, top_entries)


if __name__ == "__main__":
    main()
