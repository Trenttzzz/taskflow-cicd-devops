# Metrics After Enhancement

## Sistem yang Dievaluasi

Enhancement yang dievaluasi adalah AI Failure Intelligence pada pipeline TaskFlow. Sistem menambahkan status guard, log collection, log cleaning, embedding retrieval, LLM report generation, dan fallback behavior.

Model yang digunakan:

- Embedding: `gemini-embedding-2`
- LLM report: `gemini-3.1-flash-lite`

## Success Path

Success path sudah diuji secara lokal dengan status semua job `success`.

Command:

```bash
CI_RESULT=success SECURITY_RESULT=success CD_RESULT=success TAG_STABLE_RESULT=success python3 scripts/failure_status.py
GEMINI_API_KEY= python3 scripts/generate_failure_report.py
```

Output:

```text
Pipeline succeeded. No AI failure analysis needed.
Pipeline sukses. Embedding API dan LLM API tidak dipanggil.
```

Hasil:

| Metrik | Nilai |
| --- | ---: |
| `should_analyze` | false |
| Call ke `gemini-embedding-2` | 0 |
| Call ke `gemini-3.1-flash-lite` | 0 |
| Diagnosis report dibuat | Tidak |
| Success status dibuat | Ya |

## Failure Path dengan Real API Key

Failure path sudah diuji secara lokal menggunakan `GEMINI_API_KEY` dari `.env`.

Command:

```bash
CI_RESULT=failure SECURITY_RESULT=success CD_RESULT=skipped TAG_STABLE_RESULT=skipped python3 scripts/failure_status.py
python3 scripts/build_embedding_index.py
python3 scripts/retrieve_similar_failures.py --query ai-reports/current-failure.cleaned.log --top-k 3
python3 scripts/generate_failure_report.py
```

Output terminal:

```text
Pipeline failed. AI failure analysis required.
Embedding index contains 5 entries.
Report AI failure berhasil dibuat.
```

## Retrieval Result - Single Coverage Failure

Input failure adalah coverage gate failure dengan total coverage 72.8 persen, di bawah threshold 75 persen.

Top-3 retrieval:

| Rank | Failure ID | Category | Similarity | Expected Category Match |
| ---: | --- | --- | ---: | --- |
| 1 | synthetic-001-coverage-gate | coverage-gate | 0.8830 | Ya |
| 2 | synthetic-004-security-scan | security-scan | 0.7099 | Tidak |
| 3 | synthetic-003-postgres-timeout | integration-postgres | 0.7091 | Tidak |

Metrik retrieval untuk skenario ini:

| Metrik | Nilai |
| --- | ---: |
| Top-1 accuracy | 1/1 |
| Top-3 accuracy | 1/1 |
| Similarity top-1 | 0.8830 |
| Knowledge base size | 5 entries |

## Controlled Failure Scenario Evaluation

Setelah evaluasi satu skenario coverage gate, evaluasi diperluas menjadi 15 repeated controlled failure scenarios. Skenario ini berada di `evaluations/controlled-failure-logs/` dan dijalankan menggunakan:

```bash
python3 scripts/evaluate_controlled_failures.py
```

Script tersebut menjalankan cleaning, OOVD-inspired filtering, retrieval top-3 dalam dua mode, lalu menghasilkan `evaluations/generated/descriptive-metrics.json` dan `evaluations/generated/descriptive-metrics.md`.

Ringkasan hasil:

| Mode | Controlled Scenarios | Top-1 Accuracy | Top-3 Accuracy | MRR | Mean Top-1 Similarity |
| --- | ---: | ---: | ---: | ---: | ---: |
| full_cleaned_log | 15 | 15/15 | 15/15 | 1.0000 | 0.8559 |
| oovd_focused_log | 15 | 14/15 | 15/15 | 0.9667 | 0.8192 |

Hasil per skenario:

| Scenario | Expected | Full Top-1 | Full Expected Rank | OOVD Top-1 | OOVD Expected Rank | OOVD Lines |
| --- | --- | --- | --- | --- | --- | ---: |
| coverage-gate | coverage-gate | coverage-gate | 1 | coverage-gate | 1 | 2 |
| coverage-gate-unicode | coverage-gate | coverage-gate | 1 | coverage-gate | 1 | 2 |
| coverage-gate-new-package | coverage-gate | coverage-gate | 1 | coverage-gate | 1 | 3 |
| docker-build | docker-build | docker-build | 1 | docker-build | 1 | 6 |
| docker-build-go-mod | docker-build | docker-build | 1 | docker-build | 1 | 5 |
| docker-build-copy-path | docker-build | docker-build | 1 | docker-build | 1 | 6 |
| postgres-timeout | integration-postgres | integration-postgres | 1 | integration-postgres | 1 | 4 |
| postgres-auth | integration-postgres | integration-postgres | 1 | integration-postgres | 1 | 4 |
| postgres-migration | integration-postgres | integration-postgres | 1 | integration-postgres | 1 | 5 |
| security-scan | security-scan | security-scan | 1 | security-scan | 1 | 5 |
| security-gosec | security-scan | security-scan | 1 | security-scan | 1 | 5 |
| security-govulncheck | security-scan | security-scan | 1 | security-scan | 1 | 3 |
| smoke-test-health | smoke-test-health | smoke-test-health | 1 | smoke-test-health | 1 | 5 |
| smoke-test-stats | smoke-test-health | smoke-test-health | 1 | smoke-test-health | 1 | 4 |
| smoke-test-container-crash | smoke-test-health | smoke-test-health | 1 | integration-postgres | 2 | 5 |

Paired comparison:

| Metric | Full Wins | OOVD Wins | Ties | Exact Sign Test p-value |
| --- | ---: | ---: | ---: | ---: |
| Top-1 correctness | 1 | 0 | 14 | 1.0000 |

Interpretasi:

Metrik ini menunjukkan bahwa full-log retrieval memberi kategori yang benar pada 15 repeated controlled failure scenarios. OOVD-focused retrieval juga stabil untuk Top-3, tetapi satu skenario container crash lebih tepat jika memakai full cleaned log. Exact sign test hanya dihitung pada disagreement dan tidak menunjukkan improvement signifikan karena hampir semua trial tie.

## OOVD-Inspired Filtering Result

Filtering yang ditambahkan bukan OOVD model penuh seperti Li et al. (2025). Implementasi ini adalah pendekatan ringan yang membandingkan token log dengan vocabulary CI umum, lalu memberi score pada baris yang mengandung token tidak biasa. Outputnya disimpan di file `*.oovd.json`.

Contoh pada coverage gate:

```json
{
  "line_number": 1,
  "score": 3,
  "tokens": ["atomic", "covermode", "coverprofile"],
  "line": "Run go test ./... -coverprofile=coverage.out -covermode=atomic"
}
```

Contoh pada PostgreSQL timeout:

```json
{
  "score": 13,
  "tokens": ["connect", "connection", "dapat", "dial", "dijangkau", "failed", "gagal", "host", "konek", "refused", "tcp", "tidak"],
  "line": "postgres_test.go:27: gagal konek ke postgres: database tidak dapat dijangkau..."
}
```

Output ini dipakai sebagai sinyal tambahan untuk report LLM. Tujuannya bukan menggantikan retrieval, tetapi membantu menonjolkan baris log yang failure-relevant.

## AI Report Result

Report yang dibuat menyimpulkan:

```text
Pipeline gagal karena total coverage yang tercapai sebesar 72.8%, yang mana berada di bawah ambang batas minimum sebesar 75%.
```

Evidence yang ditampilkan:

```text
Total coverage: 72.8%
Coverage 72.8% is below 75%
Error: Process completed with exit code 1.
```

Suggested debugging steps:

```text
1. Jalankan command go test ./... -coverprofile=coverage.out -covermode=atomic.
2. Analisis coverage.out untuk package/fungsi coverage rendah.
3. Tambahkan unit test sampai coverage minimal 75%.
```

## Live GitHub Actions Failure Demo

Live failure demo dilakukan dengan intentional coverage gate failure. Threshold coverage sementara dinaikkan menjadi 101 persen agar pipeline gagal secara terkontrol, lalu dikembalikan lagi ke threshold normal setelah bukti failure terkumpul.

Ringkasan artifact `ai-reports` dari GitHub Actions:

| Metrik | Nilai |
| --- | ---: |
| Failed job | `ci` |
| Coverage aktual | 78.9% |
| Threshold demo sementara | 101% |
| Expected category | `coverage-gate` |
| Top-1 category | `coverage-gate` |
| Top-1 similarity | 0.8329 |
| AI report dibuat | Ya |

Evidence utama:

```text
Total coverage: 78.9%
Coverage 78.9% is below 101%
```

Report menyimpulkan bahwa failure disebabkan oleh coverage gate misconfiguration karena threshold 101 persen tidak realistis. Ini sesuai dengan tujuan demo: membuktikan bahwa sistem dapat membaca failure log dari GitHub Actions, mengambil similar failure yang relevan, dan membuat debugging report berbasis evidence.

## Automatic Failure Archive

Implementasi terbaru menambahkan archive provisional ke branch `failure-history`. Archive dijalankan setelah retrieval dan report agar current failure tidak menjadi kandidat bagi dirinya sendiri.

Local unit test membuktikan:

| Quality Check | Hasil Lokal |
| --- | --- |
| Failure valid menghasilkan provisional entry | Lulus |
| Duplicate sanitized log tidak menambah entry | Lulus |
| Secret dimasking ulang sebelum disimpan | Lulus |
| Success status ditolak | Lulus |
| Corrupt metadata tidak ditimpa | Lulus |
| Entry `validated: false` tidak masuk index | Lulus |
| Entry real tervalidasi dan lengkap dapat dibaca index | Lulus |

Hasil ini membuktikan logic archive secara lokal. Penulisan otomatis ke branch `failure-history` belum boleh diklaim berhasil di GitHub Actions sampai workflow terbaru dipush dan controlled failure dijalankan.

## Fallback Path Tanpa API Key

Fallback path juga diuji dengan `GEMINI_API_KEY` kosong.

Output:

```text
Pipeline failed. AI failure analysis required.
GEMINI_API_KEY is not set. Embedding index was not generated.
Laporan fallback dibuat tanpa GEMINI_API_KEY.
```

Hasil:

| Metrik | Nilai |
| --- | --- |
| Pipeline utama tetap bisa lanjut | Ya |
| Fallback report dibuat | Ya |
| Secret tidak dibutuhkan untuk fallback | Ya |
| Retrieval tersedia | Tidak |

## Status Evaluasi Saat Ini

Evaluasi yang sudah selesai:

- Success path tanpa AI call.
- Failure path dengan real API key.
- Failure fallback tanpa API key.
- Top-1 dan Top-3 retrieval untuk coverage gate.
- Top-1 dan Top-3 retrieval untuk 15 repeated controlled failure scenarios.
- OOVD-inspired line extraction untuk 15 repeated controlled failure scenarios.
- Perbandingan deskriptif full cleaned log vs OOVD-focused query dengan exact sign test terbatas.
- Live GitHub Actions coverage gate failure demo dengan Top-1 category `coverage-gate`.
- Unit test automatic archive, deduplication, secret masking, dan validation gate.

Evaluasi yang belum selesai:

- Live verification job `archive-failure` dan branch `failure-history`.
- Telegram failure summary live.
- Diagnosis time manual dengan stopwatch.
- Report usefulness score dari anggota tim.
