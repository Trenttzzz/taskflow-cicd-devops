# Pembagian Tugas Final Project

## Topik Project

**CI/CD with AI Failure Intelligence**

Project ini mengubah pipeline TaskFlow dari pipeline CI/CD biasa menjadi pipeline yang dapat memberi diagnosis failure berbasis AI. Pekerjaan dimulai dari penghapusan GKE sebagai jalur deployment utama, lalu dilanjutkan dengan pembuatan AI Failure Intelligence yang hanya berjalan saat pipeline gagal.

## Prinsip Kerja Kelompok

- Semua anggota memahami alur besar: CI/CD tanpa GKE, failure detection, log cleaning, embedding retrieval, LLM report, evaluasi, dokumentasi, dan presentasi.
- Setiap anggota memiliki output yang bisa diverifikasi melalui file, test, dokumentasi, atau hasil demo.
- AI tidak dipanggil saat pipeline sukses.
- Secret seperti `GEMINI_API_KEY`, `TELEGRAM_TOKEN`, dan `TELEGRAM_TO` tidak boleh ditulis ke source code.
- Dokumentasi GKE lama boleh dipertahankan sebagai legacy, tetapi bukan jalur utama final project.

## Pembagian Peran

| Anggota | Peran Utama | Fokus Pekerjaan | Output Utama |
| --- | --- | --- | --- |
| Orang 1 | Konseptor dan implementator awal | Merancang konsep utama, menghapus GKE dari workflow, membuat struktur awal AI Failure Intelligence | Workflow awal tanpa GKE, konsep arsitektur, baseline implementasi |
| Orang 2 | CI/CD engineer | Menjaga pipeline Go, security scan, Docker build, GHCR push, smoke test, dan stable tag | Workflow CI/CD stabil dan bisa didemo |
| Orang 3 | AI retrieval engineer | Mengelola knowledge base, embedding index, retrieval similar failures, dan OOVD-inspired filtering | Failure knowledge base dan retrieval yang terukur |
| Orang 4 | LLM report engineer | Mengelola prompt, fallback report, retry behavior, dan output Markdown AI report | AI failure report berbasis evidence |
| Orang 5 | Evaluation engineer | Membuat controlled failure scenarios, repeated trials, descriptive metrics, dan analisis hasil | Folder `evaluations/` lengkap dengan angka evaluasi |
| Orang 6 | Research and documentation engineer | Menghubungkan implementasi dengan paper, menulis research summary, README, dan refleksi kelompok | Folder `research/`, README, dan `docs/refleksi-kelompok.md` |
| Orang 7 | Presentation and demo engineer | Menyiapkan alur demo, screenshot/artifact pipeline, slide, dan narasi presentasi | `presentation/slides.pdf` dan demo script |

## Detail Tugas Per Anggota

### Orang 1 - Konseptor dan Implementator Awal

Tanggung jawab:

- Menentukan arah final project: **CI/CD with AI Failure Intelligence**.
- Memulai perubahan dari penghapusan GKE sebagai jalur utama workflow.
- Menghapus kebutuhan aktif terhadap `GCP_SA_KEY`, `KUBECONFIG_BASE64`, `kubectl`, dan deployment Kubernetes dari workflow utama.
- Mendesain alur awal:
  - pipeline sukses tidak memanggil AI,
  - pipeline gagal mengaktifkan `failure-intelligence`,
  - log failure dikumpulkan,
  - log dibersihkan,
  - similar failure dicari,
  - LLM membuat report.
- Menentukan boundary agar sistem tetap sederhana dan tidak over-engineered.

Output yang harus ada:

- Workflow utama tanpa dependency GKE aktif.
- Job `failure-intelligence` sebagai fondasi awal.
- Ringkasan konsep di README atau dokumen planning.
- Penjelasan singkat alasan GKE dihapus dari workflow final.

Kriteria selesai:

- Workflow tidak membutuhkan secret GKE.
- Pipeline tetap bisa menjalankan test, security scan, build, push image, dan smoke test.
- Anggota lain bisa melanjutkan dari struktur awal yang dibuat.

### Orang 2 - CI/CD Engineer

Tanggung jawab:

- Menjaga job CI utama tetap stabil.
- Memastikan matrix Go berjalan.
- Memastikan coverage gate berjalan sesuai threshold final.
- Memastikan security scan tidak mengganggu flow utama.
- Memastikan Docker image berhasil dibuat dan dipush ke GHCR.
- Memastikan container lokal bisa dijalankan untuk smoke test.
- Memastikan `tag-stable` hanya berjalan saat workflow utama sukses.

Output yang harus ada:

- Workflow `.github/workflows/ci-cd.yml` yang stabil.
- Bukti success path dari GitHub Actions.
- Catatan command lokal untuk verifikasi.

Kriteria selesai:

- `go test ./...` sukses.
- `go test -race ./...` sukses.
- Smoke test container berhasil.
- Success path tidak memanggil embedding API atau LLM API.

### Orang 3 - AI Retrieval Engineer

Tanggung jawab:

- Menyiapkan `failure-knowledge-base/`.
- Menulis atau merapikan synthetic failure logs.
- Menjaga metadata knowledge base.
- Membuat dan memvalidasi embedding index dengan `gemini-embedding-2`.
- Memastikan retrieval memakai cosine similarity.
- Menambahkan OOVD-inspired filtering ringan sebagai sinyal pendukung, bukan pengganti retrieval utama.

Output yang harus ada:

- `failure-knowledge-base/metadata.json`.
- `failure-knowledge-base/synthetic-logs/`.
- `failure-knowledge-base/notes/`.
- `failure-knowledge-base/embeddings/embedding-index.json`.
- Script retrieval yang bisa menghasilkan top-k similar failures.

Kriteria selesai:

- Embedding index valid JSON.
- Model embedding tercatat sebagai `gemini-embedding-2`.
- Retrieval menghasilkan top-k similar failures dengan similarity score.
- Jika `GEMINI_API_KEY` tidak ada, script tidak membuat fake embedding.

### Orang 4 - LLM Report Engineer

Tanggung jawab:

- Membuat report generator untuk failure path.
- Memakai `gemini-3.1-flash-lite` sebagai explanation layer.
- Membuat prompt yang berbasis evidence log dan similar failures.
- Mencegah LLM mengarang root cause yang tidak didukung log.
- Menyiapkan fallback report jika API key tidak tersedia atau LLM API error.
- Memastikan report tidak membocorkan secret atau raw provider payload.

Output yang harus ada:

- `scripts/generate_failure_report.py`.
- `ai-reports/failure-intelligence-report.md` saat failure path.
- Fallback report saat `GEMINI_API_KEY` kosong.
- Report berbahasa Indonesia yang mudah dipakai untuk debugging.

Kriteria selesai:

- LLM hanya dipanggil saat failure.
- Success path hanya menampilkan status sukses.
- Failure path menghasilkan report yang berisi summary, likely root cause, evidence, similar failures, dan debugging steps.
- Error provider ditangani dengan retry atau fallback.

### Orang 5 - Evaluation Engineer

Tanggung jawab:

- Membuat controlled failure scenarios.
- Menjalankan repeated trials untuk mengukur stabilitas retrieval.
- Membuat descriptive metrics yang jujur dan tidak berlebihan.
- Membandingkan before dan after AI Failure Intelligence.
- Mencatat success path dan failure path secara terpisah.

Output yang harus ada:

- `evaluations/controlled-failure-scenarios.md`.
- `evaluations/metrics-before.md`.
- `evaluations/metrics-after.md`.
- `evaluations/analysis.md`.
- Data angka seperti top-1 accuracy, top-3 accuracy, similarity score, jumlah skenario, dan call AI pada success path.

Kriteria selesai:

- Evaluasi memiliki angka, bukan hanya narasi.
- Success path membuktikan AI call bernilai 0.
- Failure path menunjukkan retrieval dan report berjalan.
- Keterbatasan evaluasi ditulis jujur.

### Orang 6 - Research and Documentation Engineer

Tanggung jawab:

- Membaca dan merangkum paper sumber ide.
- Menghubungkan konsep paper dengan implementasi TaskFlow.
- Menjelaskan mengapa project memakai embedding retrieval, bukan training model besar.
- Menjelaskan mengapa LLM hanya menjadi explanation layer.
- Memperbarui README agar cara menjalankan AI Failure Intelligence jelas.
- Menulis refleksi kelompok setelah implementasi dan evaluasi selesai.

Output yang harus ada:

- `research/01-gap-analysis.md`.
- `research/02-state-of-the-art.md`.
- `research/03-design-decisions.md`.
- README yang menjelaskan setup secret, local run, success path, failure path, dan interpretasi report.
- `docs/refleksi-kelompok.md` pada tahap akhir.

Kriteria selesai:

- Research tidak hanya menyalin paper, tetapi menjelaskan adaptasi ke project.
- README bisa dipakai orang lain untuk menjalankan demo.
- Refleksi menjelaskan kontribusi anggota, kendala, keputusan teknis, dan pembelajaran.

### Orang 7 - Presentation and Demo Engineer

Tanggung jawab:

- Menyiapkan alur demo final.
- Mengumpulkan bukti GitHub Actions success dan failure.
- Menyiapkan narasi presentasi berdasarkan konsep, implementasi, evaluasi, dan hasil.
- Membuat slide yang ringkas dan berbasis evidence.
- Menyiapkan checklist demo agar presentasi tidak bergantung pada improvisasi.

Output yang harus ada:

- `presentation/slides.pdf`.
- Demo script singkat.
- Screenshot atau artifact pendukung dari success path dan failure path.
- Ringkasan hasil evaluasi yang siap dipresentasikan.

Kriteria selesai:

- Slide menjelaskan masalah, paper source, solusi, arsitektur, workflow, evaluasi, hasil, dan keterbatasan.
- Demo menunjukkan dua kondisi: pipeline sukses tanpa AI call dan pipeline gagal dengan AI report.
- Presenter bisa menjelaskan angka evaluasi secara konkret.

## Urutan Implementasi

1. Orang 1 menghapus GKE dari workflow utama dan membuat konsep awal AI Failure Intelligence.
2. Orang 2 menstabilkan CI/CD non-GKE: test, coverage, security scan, Docker, GHCR, smoke test, stable tag.
3. Orang 3 membuat knowledge base dan retrieval dengan `gemini-embedding-2`.
4. Orang 4 membuat report generator dengan `gemini-3.1-flash-lite`.
5. Orang 5 membuat controlled failure scenarios dan evaluasi angka.
6. Orang 6 menulis research, README, dan refleksi kelompok.
7. Orang 7 menyiapkan slide, demo script, dan bukti presentasi.

## Dependency Antar Tugas

| Tugas | Bergantung Pada | Alasan |
| --- | --- | --- |
| CI/CD non-GKE | Orang 1 | Struktur workflow harus jelas dulu |
| Failure status guard | Orang 1 dan Orang 2 | Perlu tahu job mana yang menjadi sumber status |
| Retrieval | Orang 3 | Perlu knowledge base dan embedding index |
| LLM report | Orang 3 dan Orang 4 | Report butuh current failure log dan similar failures |
| Evaluasi | Orang 2, Orang 3, Orang 4 | Evaluasi butuh workflow, retrieval, dan report berjalan |
| README final | Orang 2 sampai Orang 5 | README harus sesuai implementasi aktual |
| Refleksi | Semua anggota | Refleksi membutuhkan kontribusi dan kendala setiap anggota |
| Presentasi | Semua output final | Slide harus merangkum konsep, implementasi, evaluasi, dan demo |


## Catatan Koordinasi

- Orang 1 menjadi penanggung jawab arah teknis agar implementasi tidak melebar.
- Orang 2 sampai Orang 4 fokus pada sistem yang berjalan.
- Orang 5 memastikan klaim project didukung angka.
- Orang 6 memastikan project dapat dipahami dari dokumen.
- Orang 7 memastikan project dapat dipresentasikan dengan jelas.
