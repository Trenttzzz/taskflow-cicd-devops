# Panduan & Script Demonstrasi — AI Failure Intelligence

Dokumen ini berisi panduan praktis bagi presenter untuk mendemonstrasikan sistem AI Failure Intelligence secara langsung. Alur demo ini dirancang untuk menunjukkan transisi dari konsep riset (log cleaning & retrieval) ke integrasi praktis di TaskFlow API.

---

## Persiapan Sebelum Demo

1. **Aplikasi**: Pastikan repository `taskflow-cicd-devops` berada di branch `main` (atau branch demo khusus).
2. **API Key**: Pastikan file `.env` di root folder berisi `GEMINI_API_KEY` yang valid.
3. **Browser**: Buka tab browser di halaman GitHub Actions repository TaskFlow.
4. **Terminal**: Buka terminal di root workspace dan pastikan Python 3.11+ telah terinstal.
5. **Kebersihan Folder**: Hapus laporan lama di folder `ai-reports` jika ada, agar demo bersih:
   ```bash
   rm -f ai-reports/status.json ai-reports/current-failure.* ai-reports/similar-failures.json ai-reports/oovd-lines.json ai-reports/failure-intelligence-report.md ai-reports/success-status.txt
   ```

---

## SKENARIO DEMO 1: Success Path Guard (Tanpa Call AI)

**Tujuan**: Membuktikan prinsip efisiensi biaya. AI tidak dipanggil saat pipeline sukses.

### **Langkah-Langkah**:
1. Jalankan script guard dengan menyimulasikan seluruh status job adalah sukses:
   ```bash
   CI_RESULT=success SECURITY_RESULT=success CD_RESULT=success TAG_STABLE_RESULT=success python3 scripts/failure_status.py
   ```
2. Jalankan script generator report dengan API key sengaja dikosongkan untuk membuktikan AI tidak dihubungi:
   ```bash
   GEMINI_API_KEY= python3 scripts/generate_failure_report.py
   ```

### **Penjelasan Presenter ke Audiens**:
> *"Bisa kita lihat di layar terminal, ketika status job CI, Security, dan CD semuanya sukses (`success`), status guard mendeteksi bahwa analisis AI tidak diperlukan (`should_analyze = false`). Karena guard ini, pemanggilan API embedding dan API LLM adalah **0 call**. Ini menghemat kuota API dan biaya operasional selama build harian berjalan normal."*

---

## SKENARIO DEMO 2: Failure Path Lokal (Log Cleaning & Retrieval)

**Tujuan**: Menunjukkan proses pembersihan log mentah, pencarian kesamaan semantik di Knowledge Base, dan pembuatan laporan oleh LLM.

### **Langkah-Langkah**:
1. Buat folder laporan dan simulasikan log kegagalan baru dengan menyalin contoh log kegagalan coverage gate terkontrol:
   ```bash
   mkdir -p ai-reports
   cp evaluations/controlled-failure-logs/coverage-gate.log ai-reports/current-failure.log
   ```
2. Simulasikan status failure pada pipeline:
   ```bash
   CI_RESULT=failure SECURITY_RESULT=success CD_RESULT=skipped TAG_STABLE_RESULT=skipped python3 scripts/failure_status.py
   ```
3. Lakukan pembersihan log dan ekstraksi OOVD-inspired scoring:
   ```bash
   python3 scripts/clean_failure_log.py
   ```
4. Indeks ulang Knowledge Base (menggunakan model `gemini-embedding-2`):
   ```bash
   python3 scripts/build_embedding_index.py
   ```
5. Jalankan pencarian kemiripan log (retrieval) terhadap Knowledge Base:
   ```bash
   python3 scripts/retrieve_similar_failures.py --query ai-reports/current-failure.cleaned.log --top-k 3
   ```
   *(Tunjukkan output di terminal: Top-1 harus berupa `coverage-gate` dengan similarity score ~0.88)*
6. Jalankan pembuatan laporan debug berbasis Gemini:
   ```bash
   python3 scripts/generate_failure_report.py
   ```
7. Buka dan tampilkan hasil laporan Markdown:
   ```bash
   cat ai-reports/failure-intelligence-report.md
   ```

### **Penjelasan Presenter ke Audiens**:
> *"Saat terdeteksi kegagalan, script log cleaner langsung menghapus noise log standard runner dan menyensor secrets. Sistem kemudian mencari error serupa di Knowledge Base menggunakan Cosine Similarity. Hasil retrieval di terminal menunjukkan kategori `coverage-gate` berada di peringkat pertama dengan similarity 0.88. Terakhir, Gemini Flash menyusun laporan debugging di `failure-intelligence-report.md` yang menyimpulkan root cause secara tepat berdasarkan bukti nyata log, lengkap dengan command perbaikan tanpa halusinasi."*

---

## SKENARIO DEMO 3: Controlled Evaluation (Kestabilan Model)

**Tujuan**: Membuktikan kestabilan sistem pencarian kemiripan pada 15 skenario kegagalan terkontrol yang diadaptasi dari paper riset Li et al. (2025).

### **Langkah-Langkah**:
1. Jalankan script evaluasi massal otomatis:
   ```bash
   python3 scripts/evaluate_controlled_failures.py
   ```
2. Tampilkan file metrik deskriptif yang dihasilkan:
   ```bash
   cat evaluations/generated/descriptive-metrics.md
   ```

### **Penjelasan Presenter ke Audiens**:
> *"Untuk memvalidasi keandalan retrieval sebelum diterapkan ke produksi, kami menguji sistem dengan 15 skenario kegagalan terkontrol (3 variasi log untuk masing-masing 5 kategori). Hasil evaluasi di layar menunjukkan mode `full_cleaned_log` berhasil mencapai **Top-1 Accuracy 100% (15/15)** dengan Mean Similarity 0.8559. Ini membuktikan sistem kami sangat stabil mengenali variasi pola error yang serupa."*

---

## SKENARIO DEMO 4: Live GitHub Actions Demo (Penyelarasan Pipeline)

**Tujuan**: Menunjukkan integrasi live di GitHub Actions runner.

### **Langkah-Langkah**:
1. Buat branch baru untuk simulasi demo:
   ```bash
   git checkout -b demo/intentional-failure
   ```
2. Buka `.github/workflows/ci-cd.yml` di editor teks dan edit bagian coverage threshold pada job `ci`.
   * **Ubah dari**: `coverage >= 75.0`
   * **Menjadi**: `coverage >= 101.0` (Sengaja dibuat tidak realistis)
3. Commit dan push perubahan ke GitHub:
   ```bash
   git add .github/workflows/ci-cd.yml
   git commit -m "demo: trigger intentional coverage gate failure"
   git push origin demo/intentional-failure
   ```
4. Buka browser ke halaman GitHub Actions repository Anda.
   * Tunjukkan bahwa job `ci` gagal karena coverage aktual (78.9%) kurang dari 101%.
   * Tunjukkan bahwa job `failure-intelligence` langsung aktif berjalan.
   * Setelah selesai, tunjukkan tab **Artifacts** di run summary, lalu unduh dan buka berkas `failure-intelligence-report.md`.
5. **Revert Perubahan** setelah presentasi agar branch tetap bersih:
   ```bash
   git checkout main
   git branch -D demo/intentional-failure
   git push origin --delete demo/intentional-failure
   ```

### **Penjelasan Presenter ke Audiens**:
> *"Kami memicu kegagalan live di runner GitHub Actions dengan menetapkan threshold coverage ke 101%. Job `ci` langsung gagal secara otomatis. Job AI Failure Intelligence kami mendeteksi kegagalan tersebut, mengunduh log GHA secara real-time, membersihkannya, dan mencocokkannya ke database kegagalan dengan nilai similarity **0.8329**. Artifact laporan Markdown langsung tersedia di halaman GitHub Actions untuk diunduh developer."*

---

## SKENARIO DEMO 5: Fallback Path (Uji Tanpa API Key)

**Tujuan**: Membuktikan ketahanan pipeline (tidak crash) jika terjadi kendala pada API key atau jaringan.

### **Langkah-Langkah**:
1. Simulasikan kegagalan dan jalankan generator report dengan menghapus `GEMINI_API_KEY` dari environment variables:
   ```bash
   mkdir -p ai-reports
   cp evaluations/controlled-failure-logs/coverage-gate.log ai-reports/current-failure.log
   CI_RESULT=failure SECURITY_RESULT=success CD_RESULT=skipped TAG_STABLE_RESULT=skipped python3 scripts/failure_status.py
   python3 scripts/clean_failure_log.py
   GEMINI_API_KEY= python3 scripts/generate_failure_report.py
   ```
2. Buka laporan fallback yang dihasilkan:
   ```bash
   cat ai-reports/failure-intelligence-report.md
   ```

### **Penjelasan Presenter ke Audiens**:
> *"Jika terjadi downtime pada Gemini API atau API key tidak diset, pipeline CI/CD utama kelompok kami tidak boleh ikut rusak atau macet. Seperti yang terlihat di terminal, generator kami secara cerdas beralih ke fallback path, menghasilkan laporan kegagalan dasar berbasis status job lokal tanpa merusak alur deployment."*
