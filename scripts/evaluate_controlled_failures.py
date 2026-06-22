#!/usr/bin/env python3
"""Evaluasi retrieval untuk controlled failure logs."""

import json
import math
import subprocess
import sys
from pathlib import Path

try:
    from env_loader import load_dotenv
except ModuleNotFoundError:
    from scripts.env_loader import load_dotenv


SCENARIOS = [
    ("coverage-gate", "coverage-gate"),
    ("coverage-gate-unicode", "coverage-gate"),
    ("coverage-gate-new-package", "coverage-gate"),
    ("docker-build", "docker-build"),
    ("docker-build-go-mod", "docker-build"),
    ("docker-build-copy-path", "docker-build"),
    ("postgres-timeout", "integration-postgres"),
    ("postgres-auth", "integration-postgres"),
    ("postgres-migration", "integration-postgres"),
    ("security-scan", "security-scan"),
    ("security-gosec", "security-scan"),
    ("security-govulncheck", "security-scan"),
    ("smoke-test-health", "smoke-test-health"),
    ("smoke-test-stats", "smoke-test-health"),
    ("smoke-test-container-crash", "smoke-test-health"),
]
SCENARIO_DIR = Path("evaluations/controlled-failure-logs")
OUTPUT_DIR = Path("evaluations/generated")
METRICS_JSON = OUTPUT_DIR / "descriptive-metrics.json"
METRICS_MD = OUTPUT_DIR / "descriptive-metrics.md"


def run_command(command):
    result = subprocess.run(command, check=False, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def expected_rank(top_k, expected_category):
    for index, item in enumerate(top_k, start=1):
        if item.get("category") == expected_category:
            return index
    return None


def reciprocal_rank(rank):
    if rank is None:
        return 0.0
    return 1.0 / rank


def evaluate_query(query_file, expected_category):
    run_command(
        [
            sys.executable,
            "scripts/retrieve_similar_failures.py",
            "--query",
            str(query_file),
            "--top-k",
            "3",
        ]
    )
    retrieval = read_json(Path("ai-reports/similar-failures.json"))
    top_k = retrieval.get("top_k", [])
    top_1 = top_k[0] if top_k else {}
    rank = expected_rank(top_k, expected_category)
    return {
        "top_1_category": top_1.get("category"),
        "top_1_similarity": top_1.get("similarity"),
        "expected_rank": rank,
        "reciprocal_rank": round(reciprocal_rank(rank), 4),
        "top_1_correct": rank == 1,
        "top_3_correct": rank is not None,
        "top_k": top_k,
    }


def write_oovd_query(oovd_json, fallback_query, output_file):
    oovd = read_json(oovd_json)
    lines = [item.get("line", "") for item in oovd.get("items", []) if item.get("line")]
    if not lines:
        lines = Path(fallback_query).read_text(encoding="utf-8", errors="replace").splitlines()
    output_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return oovd


def evaluate_scenario(scenario_id, expected_category):
    raw_log = SCENARIO_DIR / f"{scenario_id}.log"
    cleaned_log = OUTPUT_DIR / f"{scenario_id}.cleaned.log"
    oovd_json = OUTPUT_DIR / f"{scenario_id}.oovd.json"
    oovd_query = OUTPUT_DIR / f"{scenario_id}.oovd-query.log"

    run_command(
        [
            sys.executable,
            "scripts/clean_failure_log.py",
            "--input",
            str(raw_log),
            "--output",
            str(cleaned_log),
            "--oov-output",
            str(oovd_json),
        ]
    )
    oovd = write_oovd_query(oovd_json, cleaned_log, oovd_query)
    full_result = evaluate_query(cleaned_log, expected_category)
    oovd_result = evaluate_query(oovd_query, expected_category)

    return {
        "scenario_id": scenario_id,
        "expected_category": expected_category,
        "oovd_line_count": len(oovd.get("items", [])),
        "modes": {
            "full_cleaned_log": full_result,
            "oovd_focused_log": oovd_result,
        },
    }


def summarize_mode(results, mode):
    total = len(results)
    top_1 = sum(1 for item in results if item["modes"][mode]["top_1_correct"])
    top_3 = sum(1 for item in results if item["modes"][mode]["top_3_correct"])
    mrr = sum(item["modes"][mode]["reciprocal_rank"] for item in results) / total
    similarities = [
        item["modes"][mode]["top_1_similarity"]
        for item in results
        if item["modes"][mode]["top_1_similarity"] is not None
    ]
    mean_similarity = sum(similarities) / len(similarities) if similarities else 0.0
    return {
        "scenario_count": total,
        "top_1_accuracy": top_1,
        "top_3_accuracy": top_3,
        "mean_reciprocal_rank": round(mrr, 4),
        "mean_top_1_similarity": round(mean_similarity, 4),
    }


def exact_sign_test_p_value(left_wins, right_wins):
    trials = left_wins + right_wins
    if trials == 0:
        return 1.0
    smaller = min(left_wins, right_wins)
    probability = sum(math.comb(trials, k) for k in range(smaller + 1)) / (2**trials)
    return round(min(1.0, 2 * probability), 4)


def paired_comparison(results):
    comparisons = {}
    for metric in ["top_1_correct", "top_3_correct"]:
        full_wins = 0
        oovd_wins = 0
        ties = 0
        for item in results:
            full = item["modes"]["full_cleaned_log"][metric]
            oovd = item["modes"]["oovd_focused_log"][metric]
            if full == oovd:
                ties += 1
            elif full:
                full_wins += 1
            else:
                oovd_wins += 1
        comparisons[metric] = {
            "full_cleaned_log_wins": full_wins,
            "oovd_focused_log_wins": oovd_wins,
            "ties": ties,
            "exact_sign_test_p_value": exact_sign_test_p_value(full_wins, oovd_wins),
            "interpretation": "p-value is descriptive only; controlled dataset is small.",
        }
    return comparisons


def write_markdown(results, payload):
    rows = []
    for item in results:
        full = item["modes"]["full_cleaned_log"]
        oovd = item["modes"]["oovd_focused_log"]
        rows.append(
            "| {scenario} | {expected} | {full_top1} | {full_rank} | {oovd_top1} | {oovd_rank} | {oovd_lines} |".format(
                scenario=item["scenario_id"],
                expected=item["expected_category"],
                full_top1=full["top_1_category"],
                full_rank=full["expected_rank"] or "not-found",
                oovd_top1=oovd["top_1_category"],
                oovd_rank=oovd["expected_rank"] or "not-found",
                oovd_lines=item["oovd_line_count"],
            )
        )

    full_summary = payload["summary"]["full_cleaned_log"]
    oovd_summary = payload["summary"]["oovd_focused_log"]
    top_1_comparison = payload["paired_comparison"]["top_1_correct"]
    top_3_comparison = payload["paired_comparison"]["top_3_correct"]
    text = f"""# Generated Descriptive Metrics

Generated by `scripts/evaluate_controlled_failures.py`.

## Summary

| Mode | Scenarios | Top-1 Accuracy | Top-3 Accuracy | MRR | Mean Top-1 Similarity |
| --- | ---: | ---: | ---: | ---: | ---: |
| full_cleaned_log | {full_summary['scenario_count']} | {full_summary['top_1_accuracy']}/{full_summary['scenario_count']} | {full_summary['top_3_accuracy']}/{full_summary['scenario_count']} | {full_summary['mean_reciprocal_rank']} | {full_summary['mean_top_1_similarity']} |
| oovd_focused_log | {oovd_summary['scenario_count']} | {oovd_summary['top_1_accuracy']}/{oovd_summary['scenario_count']} | {oovd_summary['top_3_accuracy']}/{oovd_summary['scenario_count']} | {oovd_summary['mean_reciprocal_rank']} | {oovd_summary['mean_top_1_similarity']} |

## Scenario Results

| Scenario | Expected | Full Top-1 | Full Expected Rank | OOVD Top-1 | OOVD Expected Rank | OOVD Lines |
| --- | --- | --- | --- | --- | --- | ---: |
{chr(10).join(rows)}

## Paired Comparison

| Metric | Full Wins | OOVD Wins | Ties | Exact Sign Test p-value |
| --- | ---: | ---: | ---: | ---: |
| Top-1 correctness | {top_1_comparison['full_cleaned_log_wins']} | {top_1_comparison['oovd_focused_log_wins']} | {top_1_comparison['ties']} | {top_1_comparison['exact_sign_test_p_value']} |
| Top-3 correctness | {top_3_comparison['full_cleaned_log_wins']} | {top_3_comparison['oovd_focused_log_wins']} | {top_3_comparison['ties']} | {top_3_comparison['exact_sign_test_p_value']} |

## Interpretation

Metrik ini masih bersifat controlled evaluation, bukan bukti generalisasi produksi. Exact sign test hanya dihitung pada disagreement antara dua mode. Jika hampir semua trial tie, p-value tidak menunjukkan improvement walaupun kedua mode sama-sama akurat.
"""
    METRICS_MD.write_text(text, encoding="utf-8")


def main():
    load_dotenv()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results = [evaluate_scenario(*scenario) for scenario in SCENARIOS]
    payload = {
        "summary": {
            "full_cleaned_log": summarize_mode(results, "full_cleaned_log"),
            "oovd_focused_log": summarize_mode(results, "oovd_focused_log"),
        },
        "paired_comparison": paired_comparison(results),
        "results": results,
    }
    METRICS_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    write_markdown(results, payload)
    print(f"Evaluated {len(results)} controlled failure scenarios in 2 retrieval modes.")


if __name__ == "__main__":
    main()
