# Design Decisions - AI Failure Intelligence

## Decision 1 - Fokus pada Failure Retrieval, Bukan Build Prediction

TaskFlow memilih failure retrieval karena problem praktis yang dihadapi adalah diagnosis setelah pipeline gagal. Saidani et al. (2022) menunjukkan bahwa CI build prediction dengan LSTM membutuhkan histori build besar, tuning, dan evaluasi kompleks. Dataset TaskFlow belum cukup untuk training model seperti DL-CIBuild.

Karena itu, implementasi memilih pendekatan yang lebih realistis: ketika failure terjadi, sistem mencari failure serupa di knowledge base dan membuat report debugging. Keputusan ini tetap berbasis paper karena Saidani et al. membuktikan bahwa historical CI data bernilai untuk automation, tetapi scope implementasi disesuaikan dengan constraint proyek.

## Decision 2 - Menggunakan Top-3 Similar Failures

Li et al. (2025) mengevaluasi near-duplicate failure dengan Top-K retrieval dan memilih K = 5 karena developer tidak realistis melihat rekomendasi terlalu banyak. TaskFlow memakai Top-3 agar report tetap ringkas untuk demo dan Telegram summary.

Keputusan ini membuat output lebih actionable. Developer mendapat beberapa candidate failure yang relevan, tetapi tidak dibanjiri daftar panjang. Selain itu, Top-3 memudahkan evaluasi sederhana seperti Top-1 accuracy dan Top-3 accuracy.

## Decision 3 - Membersihkan Log Sebelum Retrieval dan LLM

Li et al. (2025) menunjukkan bahwa raw CI logs mengandung banyak noise dan bahwa filtering dapat meningkatkan retrieval quality. TaskFlow menerapkan log cleaning yang lebih sederhana:

- hapus ANSI code,
- hapus timestamp tertentu,
- mask token dan secret pattern,
- batasi jumlah baris,
- pertahankan baris penting seperti error, failed, coverage, timeout, gosec, govulncheck, health, dan stats.

TaskFlow juga menambahkan OOVD-inspired filtering ringan. Sistem tidak melatih vocabulary dari passing logs seperti Li et al. (2025), tetapi memakai vocabulary CI umum dan memberi score pada baris yang mengandung token tidak biasa. Output ini disimpan sebagai `oovd-lines.json` dan diberikan ke LLM sebagai suspicious lines.

Keputusan ini juga mendukung security karena raw log tidak langsung dikirim ke LLM tanpa masking.

## Decision 4 - Menggunakan `gemini-embedding-2`

TaskFlow menggunakan `gemini-embedding-2` untuk mengubah failure log menjadi vector embedding. Keputusan ini dipilih karena semantic embedding lebih cocok untuk knowledge base kecil dan kategori failure yang beragam. Pendekatan ini juga menghindari dependency berat seperti local transformer model.

Dalam konteks Li et al. (2025), embedding menggantikan kombinasi text distance metrics. Prinsipnya tetap sama: current failure dibandingkan dengan historical atau synthetic failure entries menggunakan similarity score. Untuk menjaga reproducibility, index menyimpan model name, output dimensionality, dan text hash.

## Decision 5 - Menggunakan Cosine Similarity Lokal

Setelah embedding didapat, TaskFlow menghitung cosine similarity secara lokal. Keputusan ini menjaga retrieval tetap sederhana dan transparan. Similarity score dapat ditampilkan ke report dan dievaluasi.

Cosine similarity juga selaras dengan konsep similarity analysis pada Li et al. (2025), meskipun paper tersebut memakai beberapa distance metrics dan Z-score sum. TaskFlow memilih satu metric agar implementasi kecil, mudah dibaca, dan cukup untuk demo.

## Decision 6 - LLM Sebagai Explanation Layer

Gemma `gemma-4-31b-it` tidak digunakan sebagai classifier utama. Root cause candidate berasal dari retrieved failures dan evidence log. LLM hanya menyusun summary, likely root cause, evidence, dan debugging steps.

Keputusan ini mengurangi risiko hallucination. Prompt membatasi model agar tidak membuat root cause di luar evidence. Jika evidence tidak cukup, report harus menyatakan bahwa evidence belum cukup.

## Decision 7 - Synthetic Logs untuk Mengatasi Cold-Start

Saidani et al. (2022) menyoroti bahwa failed builds cenderung lebih sedikit dibanding passed builds. Dalam TaskFlow, real failed logs juga belum banyak. Karena itu synthetic validated logs dipakai untuk knowledge base awal.

Synthetic logs tidak dianggap setara dengan real evidence. Metadata menyimpan `source_type: synthetic` dan `validated: true`. Ke depan, real failed GitHub Actions logs harus ditambahkan ke `failure-knowledge-base/real-logs/` agar grounding lebih kuat.

## Decision 8 - AI Hanya Dipanggil Saat Failure

Sistem tidak memanggil embedding API atau LLM saat pipeline sukses. `failure-intelligence` tetap berjalan dengan `if: always()` agar bisa membaca status semua job, tetapi script langsung berhenti jika tidak ada failure.

Keputusan ini penting untuk efisiensi biaya, latency, dan noise. Saat sukses, output cukup menyatakan bahwa tidak ada AI failure analysis yang diperlukan.

## Decision 9 - Fallback Saat API Key Tidak Tersedia

Jika `GEMINI_API_KEY` tidak tersedia, pipeline tidak boleh gagal hanya karena failure intelligence tidak bisa memanggil AI. Sistem membuat fallback report berbasis log dan status pipeline.

Keputusan ini penting karena AI layer adalah diagnostic enhancement, bukan gate utama. Gate utama tetap CI, security, Docker build, dan smoke test.

## Decision 10 - Evaluasi Mengikuti Top-K Retrieval dan Usefulness

Berdasarkan Li et al. (2025), evaluasi utama retrieval memakai Top-K. Berdasarkan kebutuhan praktis TaskFlow, evaluasi juga mengukur usefulness:

- apakah kategori top-1 benar,
- apakah kategori yang benar muncul di top-3,
- apakah report menyebut evidence log yang tepat,
- apakah report memberi debugging steps yang bisa dijalankan,
- berapa overhead waktu AI layer.

Evaluasi juga memakai repeated controlled trials agar setiap kategori diuji dengan beberapa variasi log, bukan satu contoh saja. Exact sign test hanya dipakai sebagai catatan deskriptif untuk membandingkan full cleaned log dan OOVD-focused query pada dataset kecil. Evaluasi ini lebih sesuai daripada AUC/F1 LSTM karena TaskFlow tidak membangun build prediction classifier.
